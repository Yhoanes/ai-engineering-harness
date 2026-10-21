from pathlib import Path

import pytest

from engine.execution.models import (
    ExecutionDiagnostics,
    ExecutionPurpose,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from engine.orchestrator.engine import ExecutionProvider, HarnessEngine


class FakeProvider(ExecutionProvider):
    def __init__(self):
        self.call_count = 0
        self.last_request = None
        self._provider_id = "fake"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.call_count += 1
        self.last_request = request
        return ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            provider_id=self.provider_id,
            reported_changed_files=frozenset(),
            output_text="fake result",
            diagnostics=ExecutionDiagnostics()
        )

def create_fake_task(repo_root: Path, project_id: str, task_id: str, scope_override=None, assigned_workflow="implement-task", assigned_specialists=None):  # noqa: E501
    import yaml

    from core.context.metadata_paths import MetadataPaths
    paths = MetadataPaths(repo_root)
    contract_path = paths.task_contract(project_id, task_id)
    contract_path.parent.mkdir(parents=True, exist_ok=True)

    task_data = {
        "task_id": task_id,
        "task_type": "standard",
        "title": "Fake task",
        "project": project_id,
        "status": "in_progress",
        "approval_status": "approved",
        "approved_by": "Yhoanes",
        "approved_at": "2026-08-31T12:00:00Z",
        "acceptance_status": "pending",
        "evidence": {},
        "created_at": "2026-08-31T12:00:00Z",
        "assigned_workflow": assigned_workflow,
        "assigned_specialists": assigned_specialists or ["harness-maintainer"],
        "scope": scope_override or {
            "planned_paths": {
                "modify": {"mode": "allow_list", "values": ["some/file.py"]},
                "read": {"mode": "unrestricted"}
            },
            "allowed_actions": {
                "terminal": {"mode": "unrestricted"},
                "network_allowed": True
            },
            "forbidden_actions": ["rm -rf"]
        }
    }

    with contract_path.open('w', encoding='utf-8') as f:
        yaml.dump(task_data, f)
    return contract_path

def test_engine_valid_flow(tmp_path):
    create_fake_task(tmp_path, "test-proj", "HARNESS-0001")

    # We need a matrix for validation to pass
    matrix_path = tmp_path / "core" / "authority"
    matrix_path.mkdir(parents=True, exist_ok=True)
    with (matrix_path / "authority-matrix.yaml").open('w', encoding='utf-8') as f:
        f.write('''
specialists:
  harness-maintainer:
    execution:
      read_paths:
        mode: unrestricted
      modify_paths:
        mode: allow_list
        values:
          - "**/*"
      terminal_commands:
        mode: unrestricted
      network_allowed: true
''')

    provider = FakeProvider()
    engine = HarnessEngine(repo_root=tmp_path, provider=provider)
    result = engine.run_task("test-proj", "HARNESS-0001", "intent")

    assert provider.call_count == 1
    req = provider.last_request
    assert req.purpose == ExecutionPurpose.IMPLEMENT
    assert req.specialist_role == "harness-maintainer"

    caps = req.capabilities
    assert caps.read_paths.mode.value == "unrestricted"
    assert caps.terminal_allowed is True
    assert caps.terminal_allowed_commands.mode.value == "unrestricted"
    assert caps.network_allowed is True
    assert caps.modify_paths.mode.value == "allow_list"
    assert "some/file.py" in caps.modify_paths.values
    assert "rm -rf" in caps.forbidden_actions
    assert req.context_bundle is not None
    assert req.timeout_seconds is None

    assert result.status == ExecutionStatus.COMPLETED

def test_engine_unsupported_workflow(tmp_path):
    create_fake_task(tmp_path, "test-proj", "HARNESS-0001", assigned_workflow="plan-task")
    provider = FakeProvider()
    engine = HarnessEngine(repo_root=tmp_path, provider=provider)
    with pytest.raises(ValueError, match="Unsupported workflow: plan-task"):
        engine.run_task("test-proj", "HARNESS-0001", "intent")
    assert provider.call_count == 0

def test_engine_authority_rejection(tmp_path):
    # network=False in matrix, but Task asks for True
    create_fake_task(tmp_path, "test-proj", "HARNESS-0001")
    matrix_path = tmp_path / "core" / "authority"
    matrix_path.mkdir(parents=True, exist_ok=True)
    with (matrix_path / "authority-matrix.yaml").open('w', encoding='utf-8') as f:
        f.write('''
specialists:
  harness-maintainer:
    execution:
      read_paths:
        mode: unrestricted
      modify_paths:
        mode: unrestricted
      terminal_commands:
        mode: unrestricted
      network_allowed: false
''')
    provider = FakeProvider()
    engine = HarnessEngine(repo_root=tmp_path, provider=provider)
    with pytest.raises(ValueError, match="Task network scope exceeds specialist authority."):
        engine.run_task("test-proj", "HARNESS-0001", "intent")
    assert provider.call_count == 0

def test_engine_invalid_contract(tmp_path):
    # Missing required fields -> invalid schema
    contract_path = create_fake_task(tmp_path, "test-proj", "HARNESS-0001")
    with open(contract_path, 'w') as f:
        f.write("invalid_yaml: true")
    provider = FakeProvider()
    engine = HarnessEngine(repo_root=tmp_path, provider=provider)
    with pytest.raises(ValueError, match="Task Contract validation failed"):
        engine.run_task("test-proj", "HARNESS-0001", "intent")
    assert provider.call_count == 0

def test_engine_network_bool_coercion(tmp_path):
    create_fake_task(tmp_path, "test-proj", "HARNESS-0001", scope_override={
        "planned_paths": {
            "modify": {"mode": "allow_list", "values": ["some/file.py"]},
            "read": {"mode": "unrestricted"}
        },
        "allowed_actions": {
            "terminal": {"mode": "unrestricted"},
            "network_allowed": "false"
        },
        "forbidden_actions": ["rm -rf"]
    })
    provider = FakeProvider()
    engine = HarnessEngine(repo_root=tmp_path, provider=provider)
    with pytest.raises(ValueError, match="is not of type 'boolean'"):
        engine.run_task("test-proj", "HARNESS-0001", "intent")
    assert provider.call_count == 0

def test_engine_unknown_specialist(tmp_path):
    create_fake_task(tmp_path, "test-proj", "HARNESS-0001", assigned_specialists=["unknown-specialist"])  # noqa: E501

    matrix_path = tmp_path / "core" / "authority"
    matrix_path.mkdir(parents=True, exist_ok=True)
    with (matrix_path / "authority-matrix.yaml").open('w', encoding='utf-8') as f:
        f.write('''
specialists:
  harness-maintainer:
    execution:
      read_paths:
        mode: unrestricted
      modify_paths:
        mode: allow_list
        values:
          - "**/*"
      terminal_commands:
        mode: unrestricted
      network_allowed: true
''')

    provider = FakeProvider()
    engine = HarnessEngine(repo_root=tmp_path, provider=provider)
    with pytest.raises(ValueError):
        engine.run_task("test-proj", "HARNESS-0001", "intent")
    assert provider.call_count == 0

def test_cli_composition_legacy(monkeypatch, tmp_path):
    import contextlib
    import sys
    from unittest.mock import patch
    monkeypatch.setattr(sys, 'argv', ['__main__.py', '--project', 'test', '--task-id', 'T-1', '--intent', 'do it', '--execution-mode', 'legacy'])  # noqa: E501

    with patch('adapters.antigravity.adapter.AntigravityAdapter') as mock_adapter:
        import runpy
        with contextlib.suppress(SystemExit):
                runpy.run_module('engine.runner.__main__', run_name='__main__')
        mock_adapter.assert_called_once()

def test_cli_composition_provider(monkeypatch, tmp_path):
    import contextlib
    import sys
    from unittest.mock import patch
    monkeypatch.setattr(sys, 'argv', ['__main__.py', '--project', 'test', '--task-id', 'T-1', '--intent', 'do it', '--execution-mode', 'provider'])  # noqa: E501

    with patch('engine.orchestrator.engine.HarnessEngine') as mock_engine:
        import runpy
        with contextlib.suppress(SystemExit):
            runpy.run_module('engine.runner.__main__', run_name='__main__')

        mock_engine.assert_called_once()
        kwargs = mock_engine.call_args.kwargs
        assert 'repo_root' in kwargs
        # Ensure the real provider was passed
        from adapters.antigravity.execution_provider import AntigravityExecutionProvider
        assert isinstance(kwargs['provider'], AntigravityExecutionProvider)

def test_cli_composition_no_fallback(monkeypatch, tmp_path):
    import sys
    from unittest.mock import patch
    monkeypatch.setattr(sys, 'argv', ['__main__.py', '--project', 'test', '--task-id', 'T-1', '--intent', 'do it', '--execution-mode', 'provider'])  # noqa: E501

    with patch('engine.orchestrator.engine.HarnessEngine') as mock_engine, \
         patch('adapters.antigravity.adapter.AntigravityAdapter') as mock_adapter:
        mock_engine.return_value.run_task.side_effect = ValueError("Fatal provider error")
        import runpy
        with pytest.raises(ValueError, match="Fatal provider error"):
            runpy.run_module('engine.runner.__main__', run_name='__main__')

        mock_adapter.assert_not_called()
