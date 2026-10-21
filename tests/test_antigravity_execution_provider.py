import dataclasses
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adapters.antigravity.execution_provider import AntigravityExecutionProvider
from adapters.antigravity.models import (  # noqa: E501
    AntigravityResponse,
    AuditTrailEntry,
    LegacyExecutionOutcome,
)
from engine.context.models import ContextBundle
from engine.execution.models import (
    AccessMode,
    ExecutionCapabilities,
    ExecutionIsolation,
    ExecutionPurpose,
    ExecutionRequest,
    ExecutionStatus,
    ScopedAccess,
)


@pytest.fixture
def base_request(tmp_path: Path) -> ExecutionRequest:
    return ExecutionRequest(
        project_id="test-project",
        task_id="TASK-123",
        intent="Fix the bug",
        workspace_root=tmp_path,
        purpose=ExecutionPurpose.IMPLEMENT,
        specialist_role="mock-specialist",
        context_bundle=ContextBundle(project="test-project", requested_level=0, loaded_level=0),
        capabilities=ExecutionCapabilities(
            terminal_allowed=True,
            terminal_allowed_commands=ScopedAccess(AccessMode.UNRESTRICTED, frozenset()),
            network_allowed=True,
            read_paths=ScopedAccess(AccessMode.UNRESTRICTED, frozenset()),
            modify_paths=ScopedAccess(AccessMode.UNRESTRICTED, frozenset()),
            forbidden_actions=frozenset()
        ),
        isolation=ExecutionIsolation(required=True)
    )

def test_capabilities():
    provider = AntigravityExecutionProvider()
    caps = provider.capabilities()
    assert caps.terminal_execution is True
    assert caps.network_web is True
    assert caps.native_isolation is False
    assert caps.filesystem_mutation is True
    assert caps.long_running is False

def test_valid_request(base_request: ExecutionRequest):
    provider = AntigravityExecutionProvider()
    # Should not raise
    provider._validate_supported_request(base_request)

def test_reject_unsupported_purpose(base_request: ExecutionRequest):
    req = dataclasses.replace(base_request, purpose=ExecutionPurpose.REVIEW)
    provider = AntigravityExecutionProvider()
    with pytest.raises(ValueError, match="is not supported by legacy wrapper"):
        provider.execute(req)

def test_reject_terminal_false(base_request: ExecutionRequest):
    caps = dataclasses.replace(base_request.capabilities, terminal_allowed=False, terminal_allowed_commands=ScopedAccess(AccessMode.DENY_ALL, frozenset()))  # noqa: E501
    req = dataclasses.replace(base_request, capabilities=caps)
    provider = AntigravityExecutionProvider()
    with pytest.raises(ValueError, match="requires terminal access"):
        provider.execute(req)

def test_reject_terminal_restricted(base_request: ExecutionRequest):
    caps = dataclasses.replace(base_request.capabilities, terminal_allowed_commands=ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["echo"])))  # noqa: E501
    req = dataclasses.replace(base_request, capabilities=caps)
    provider = AntigravityExecutionProvider()
    with pytest.raises(ValueError, match="requires UNRESTRICTED terminal_allowed_commands"):
        provider.execute(req)

def test_reject_network_false(base_request: ExecutionRequest):
    caps = dataclasses.replace(base_request.capabilities, network_allowed=False)
    req = dataclasses.replace(base_request, capabilities=caps)
    provider = AntigravityExecutionProvider()
    with pytest.raises(ValueError, match="requires network_allowed=True"):
        provider.execute(req)

def test_reject_read_restricted(base_request: ExecutionRequest):
    caps = dataclasses.replace(base_request.capabilities, read_paths=ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["test"])))  # noqa: E501
    req = dataclasses.replace(base_request, capabilities=caps)
    provider = AntigravityExecutionProvider()
    with pytest.raises(ValueError, match="requires UNRESTRICTED read_paths"):
        provider.execute(req)

def test_reject_forbidden_actions(base_request: ExecutionRequest):
    caps = dataclasses.replace(base_request.capabilities, forbidden_actions=frozenset(["rm -rf"]))
    req = dataclasses.replace(base_request, capabilities=caps)
    provider = AntigravityExecutionProvider()
    with pytest.raises(ValueError, match="cannot authoritatively enforce non-empty forbidden_actions"):  # noqa: E501
        provider.execute(req)



def test_execute_success(base_request: ExecutionRequest):
    provider = AntigravityExecutionProvider()

    mock_outcome = LegacyExecutionOutcome(
        trail=(AuditTrailEntry(step=1, status="completed"),),
        response=AntigravityResponse(
            raw_text="Done",
            metadata={"conversation_id": "test-conv", "duration_seconds": 12.5}
        ),
        observed_changed_files=frozenset(["src/main.py"]),
        outcome_status="completed"
    )

    with patch('adapters.antigravity.execution_provider.AutonomousRunner.run_execution', return_value=mock_outcome) as mock_run:  # noqa: E501
        result = provider.execute(base_request)

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        legacy_req = args[0]
        assert legacy_req.project == "test-project"
        assert legacy_req.assigned_specialist == "mock-specialist"
        assert legacy_req.modify_paths_mode == AccessMode.UNRESTRICTED

        assert result.status == ExecutionStatus.COMPLETED
        assert result.reported_changed_files == frozenset(["src/main.py"])
        assert result.output_text == "Done"
        assert result.execution_id == "test-conv"
        assert result.duration_seconds == 12.5

def test_execute_runtime_failure(base_request: ExecutionRequest):
    provider = AntigravityExecutionProvider()

    with patch('adapters.antigravity.execution_provider.AutonomousRunner.run_execution', side_effect=RuntimeError("agy timeout")):  # noqa: E501
        result = provider.execute(base_request)

        assert result.status == ExecutionStatus.FAILED
        assert result.provider_metadata.get("failure_kind") == "runtime"
        assert "agy timeout" in result.diagnostics.stderr

def test_execute_governance_failure(base_request: ExecutionRequest):
    provider = AntigravityExecutionProvider()

    mock_outcome = LegacyExecutionOutcome(
        trail=(AuditTrailEntry(step=1, status="failed", reason="Out-of-scope files: ['secrets.txt']"),),  # noqa: E501
        response=None,
        observed_changed_files=frozenset(),
        failure_kind="governance"
    )

    with patch('adapters.antigravity.execution_provider.AutonomousRunner.run_execution', return_value=mock_outcome):  # noqa: E501
        result = provider.execute(base_request)

        assert result.status == ExecutionStatus.FAILED
        assert result.provider_metadata.get("failure_kind") == "governance"
        assert "Out-of-scope files" in result.diagnostics.stderr

def test_execute_response_none(base_request: ExecutionRequest):
    provider = AntigravityExecutionProvider()
    mock_outcome = LegacyExecutionOutcome(
        trail=(AuditTrailEntry(step=1, status="completed"),),
        response=None,
        observed_changed_files=frozenset(),
        outcome_status="completed"
    )
    with patch('adapters.antigravity.execution_provider.AutonomousRunner.run_execution', return_value=mock_outcome):  # noqa: E501
        result = provider.execute(base_request)
        assert result.output_text == ""
        assert result.status == ExecutionStatus.COMPLETED

def test_two_executions(base_request: ExecutionRequest):
    provider = AntigravityExecutionProvider()

    mock_outcome1 = LegacyExecutionOutcome(
        trail=(AuditTrailEntry(step=1, status="completed"),),
        response=AntigravityResponse(raw_text="Run 1"),
        observed_changed_files=frozenset(["src/a.py"]),
        outcome_status="completed"
    )
    with patch('adapters.antigravity.execution_provider.AutonomousRunner.run_execution', return_value=mock_outcome1):  # noqa: E501
        r1 = provider.execute(base_request)

    mock_outcome2 = LegacyExecutionOutcome(
        trail=(AuditTrailEntry(step=1, status="completed"),),
        response=AntigravityResponse(raw_text="Run 2"),
        observed_changed_files=frozenset(["src/b.py"]),
        outcome_status="completed"
    )
    with patch('adapters.antigravity.execution_provider.AutonomousRunner.run_execution', return_value=mock_outcome2):  # noqa: E501
        r2 = provider.execute(base_request)

    assert r1.output_text == "Run 1"
    assert r2.output_text == "Run 2"
    assert r1.reported_changed_files == frozenset(["src/a.py"])
    assert r2.reported_changed_files == frozenset(["src/b.py"])

def test_is_provider():
    from engine.execution.provider import ExecutionProvider
    # Just checking it can be instantiated and has the required methods
    provider: ExecutionProvider = AntigravityExecutionProvider()
    assert hasattr(provider, "execute")
def test_executor_construction_args(base_request):
    provider = AntigravityExecutionProvider()
    req = dataclasses.replace(base_request, timeout_seconds=120)
    with patch('adapters.antigravity.execution_provider.AntigravityCliExecutor') as mock_exec, \
         patch('adapters.antigravity.execution_provider.AutonomousRunner.run_execution', return_value=LegacyExecutionOutcome((), None, frozenset())):  # noqa: E501
            provider.execute(req)
            mock_exec.assert_called_with(timeout=120.0, dangerously_skip_permissions=True)
def test_execute_incomplete(base_request: ExecutionRequest):
    provider = AntigravityExecutionProvider()
    mock_outcome = LegacyExecutionOutcome(
        trail=(),
        response=AntigravityResponse(raw_text="No fail, but exhausted"),
        observed_changed_files=frozenset(),
        failure_kind=None,
        outcome_status="incomplete"
    )
    with patch('adapters.antigravity.execution_provider.AutonomousRunner.run_execution', return_value=mock_outcome):  # noqa: E501
        result = provider.execute(base_request)

    assert result.status == ExecutionStatus.INCOMPLETE


def test_execution_provider_propagates_fields(base_request):
    provider = AntigravityExecutionProvider()
    with patch("adapters.antigravity.execution_provider.AutonomousRunner") as mock_runner:
        mock_runner_instance = mock_runner.return_value
        mock_runner_instance.run_execution.return_value = MagicMock(
            failure_kind=None,
            outcome_status="completed",
            observed_changed_files=frozenset(["a.py"]),
            response=MagicMock(raw_text="Done", metadata={})
        )

        provider.execute(base_request)

        # Verify the AntigravityRequest created inside
        args, kwargs = mock_runner_instance.run_execution.call_args
        legacy_req = args[0]
        assert legacy_req.assigned_specialist == base_request.specialist_role
        assert legacy_req.requested_workflow == "implement-task"
        assert legacy_req.context_bundle == base_request.context_bundle



def test_provider_constructor_contract():
    """
    Ensures that AntigravityExecutionProvider correctly implements
    a zero-argument constructor, as required by the ExecutionProvider protocol
    and expected by the CLI composition root.
    """
    provider = AntigravityExecutionProvider()
    assert provider is not None
    caps = provider.capabilities()
    assert caps.terminal_execution is True
