from pathlib import Path

import pytest

from engine.context.models import ContextBundle
from engine.execution.models import (
    AccessMode,
    ExecutionCapabilities,
    ExecutionDiagnostics,
    ExecutionIsolation,
    ExecutionPurpose,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ScopedAccess,
)
from engine.execution.provider import ExecutionProvider, ProviderCapabilities


def create_dummy_context() -> ContextBundle:
    return ContextBundle(
        project="dummy",
        requested_level=1,
        loaded_level=1,
    )

def create_valid_request(
    project_id="test_project",
    task_id="TEST-0001",
    intent="do something",
    specialist_role="coder",
    timeout=None,
    isolation_req=False,
) -> ExecutionRequest:
    caps = ExecutionCapabilities(
        terminal_allowed=False,
        terminal_allowed_commands=ScopedAccess(AccessMode.DENY_ALL),
        network_allowed=False,
        read_paths=ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["src/"])),
        modify_paths=ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["src/main.py"])),
        forbidden_actions=frozenset(["rm -rf"]),
    )
    return ExecutionRequest(
        project_id=project_id,
        task_id=task_id,
        workspace_root=Path("/fake/workspace"),
        intent=intent,
        purpose=ExecutionPurpose.IMPLEMENT,
        specialist_role=specialist_role,
        capabilities=caps,
        context_bundle=create_dummy_context(),
        isolation=ExecutionIsolation(required=isolation_req),
        timeout_seconds=timeout,
    )

def test_scoped_access_deny_all():
    sa = ScopedAccess(AccessMode.DENY_ALL)
    assert sa.mode == AccessMode.DENY_ALL
    assert not sa.values
    with pytest.raises(ValueError, match="values must be empty"):
        ScopedAccess(AccessMode.DENY_ALL, frozenset(["x"]))

def test_scoped_access_unrestricted():
    sa = ScopedAccess(AccessMode.UNRESTRICTED)
    assert sa.mode == AccessMode.UNRESTRICTED
    assert not sa.values
    with pytest.raises(ValueError, match="values must be empty"):
        ScopedAccess(AccessMode.UNRESTRICTED, frozenset(["x"]))

def test_scoped_access_allow_list():
    sa = ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["x"]))
    assert sa.mode == AccessMode.ALLOW_LIST
    assert "x" in sa.values
    with pytest.raises(ValueError, match="values cannot be empty"):
        ScopedAccess(AccessMode.ALLOW_LIST)

def test_terminal_allowed_false_must_be_deny_all():
    # Valid
    ExecutionCapabilities(
        terminal_allowed=False,
        terminal_allowed_commands=ScopedAccess(AccessMode.DENY_ALL),
        network_allowed=False,
        read_paths=ScopedAccess(AccessMode.DENY_ALL),
        modify_paths=ScopedAccess(AccessMode.DENY_ALL),
        forbidden_actions=frozenset(),
    )

    # Invalid: False + UNRESTRICTED
    with pytest.raises(ValueError, match="MUST be DENY_ALL"):
        ExecutionCapabilities(
            terminal_allowed=False,
            terminal_allowed_commands=ScopedAccess(AccessMode.UNRESTRICTED),
            network_allowed=False,
            read_paths=ScopedAccess(AccessMode.DENY_ALL),
            modify_paths=ScopedAccess(AccessMode.DENY_ALL),
            forbidden_actions=frozenset(),
        )

    # Invalid: False + ALLOW_LIST
    with pytest.raises(ValueError, match="MUST be DENY_ALL"):
        ExecutionCapabilities(
            terminal_allowed=False,
            terminal_allowed_commands=ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["cat"])),
            network_allowed=False,
            read_paths=ScopedAccess(AccessMode.DENY_ALL),
            modify_paths=ScopedAccess(AccessMode.DENY_ALL),
            forbidden_actions=frozenset(),
        )

def test_terminal_allowed_true_combinations():
    # True + DENY_ALL (Terminal on, but no commands allowed)
    ExecutionCapabilities(
        terminal_allowed=True,
        terminal_allowed_commands=ScopedAccess(AccessMode.DENY_ALL),
        network_allowed=False,
        read_paths=ScopedAccess(AccessMode.DENY_ALL),
        modify_paths=ScopedAccess(AccessMode.DENY_ALL),
        forbidden_actions=frozenset(),
    )

    # True + ALLOW_LIST
    ExecutionCapabilities(
        terminal_allowed=True,
        terminal_allowed_commands=ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["cat"])),
        network_allowed=False,
        read_paths=ScopedAccess(AccessMode.DENY_ALL),
        modify_paths=ScopedAccess(AccessMode.DENY_ALL),
        forbidden_actions=frozenset(),
    )

    # True + UNRESTRICTED
    ExecutionCapabilities(
        terminal_allowed=True,
        terminal_allowed_commands=ScopedAccess(AccessMode.UNRESTRICTED),
        network_allowed=False,
        read_paths=ScopedAccess(AccessMode.DENY_ALL),
        modify_paths=ScopedAccess(AccessMode.DENY_ALL),
        forbidden_actions=frozenset(),
    )

def test_valid_execution_request():
    req = create_valid_request()
    assert req.project_id == "test_project"
    assert req.purpose == ExecutionPurpose.IMPLEMENT
    assert req.workspace_root.name == "workspace"

def test_execution_request_missing_required():
    with pytest.raises(ValueError, match="project_id cannot be empty"):
        create_valid_request(project_id="")
    with pytest.raises(ValueError, match="task_id cannot be empty"):
        create_valid_request(task_id="")
    with pytest.raises(ValueError, match="intent cannot be empty"):
        create_valid_request(intent="")
    with pytest.raises(ValueError, match="specialist_role cannot be empty"):
        create_valid_request(specialist_role="")

def test_execution_request_timeout():
    req = create_valid_request(timeout=100)
    assert req.timeout_seconds == 100
    req = create_valid_request(timeout=None)
    assert req.timeout_seconds is None
    with pytest.raises(ValueError, match="timeout_seconds must be positive or None"):
        create_valid_request(timeout=0)
    with pytest.raises(ValueError, match="timeout_seconds must be positive or None"):
        create_valid_request(timeout=-5)

def test_execution_purposes():
    assert ExecutionPurpose.IMPLEMENT.value == "implement"
    assert ExecutionPurpose.TEST.value == "test"
    assert ExecutionPurpose.REVIEW.value == "review"

def test_capabilities_preserved():
    caps = ExecutionCapabilities(
        terminal_allowed=True,
        terminal_allowed_commands=ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["ls", "cat"])),
        network_allowed=True,
        read_paths=ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["docs/"])),
        modify_paths=ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["src/"])),
        forbidden_actions=frozenset(["destroy"]),
    )
    assert caps.terminal_allowed is True
    assert "ls" in caps.terminal_allowed_commands.values
    assert caps.read_paths.mode == AccessMode.ALLOW_LIST
    assert "docs/" in caps.read_paths.values
    assert caps.modify_paths.mode == AccessMode.ALLOW_LIST
    assert "src/" in caps.modify_paths.values
    assert "destroy" in caps.forbidden_actions

def test_isolation_required():
    iso = ExecutionIsolation(required=True)
    assert iso.required is True
    pc = ProviderCapabilities(
        terminal_execution=False,
        network_web=False,
        native_isolation=False,
        filesystem_mutation=False,
        long_running=False,
    )
    assert pc.native_isolation is False

def test_execution_statuses():
    assert ExecutionStatus.COMPLETED.value == "completed"
    assert ExecutionStatus.FAILED.value == "failed"
    assert ExecutionStatus.BLOCKED.value == "blocked"
    assert ExecutionStatus.INCOMPLETE.value == "incomplete"
    assert ExecutionStatus.CANCELLED.value == "cancelled"

def test_execution_result_valid():
    diag = ExecutionDiagnostics(stdout="hello", stderr="world", warnings=("warn1",))
    res = ExecutionResult(
        status=ExecutionStatus.COMPLETED,
        provider_id="fake_provider",
        reported_changed_files=frozenset(["a.txt"]),
        output_text="Done",
        diagnostics=diag,
        execution_id="123",
        duration_seconds=1.5,
        provider_metadata={"tokens": 100},
    )
    assert res.provider_id == "fake_provider"
    assert res.execution_id == "123"
    assert res.duration_seconds == 1.5
    assert "a.txt" in res.reported_changed_files
    assert res.diagnostics.stdout == "hello"
    assert res.diagnostics.stderr == "world"
    assert "warn1" in res.diagnostics.warnings

def test_execution_result_invalid():
    diag = ExecutionDiagnostics()
    with pytest.raises(ValueError, match="provider_id cannot be empty"):
        ExecutionResult(
            status=ExecutionStatus.FAILED,
            provider_id="",
            reported_changed_files=frozenset(),
            output_text="",
            diagnostics=diag,
        )
    with pytest.raises(ValueError, match="duration_seconds must be non-negative or None"):
        ExecutionResult(
            status=ExecutionStatus.FAILED,
            provider_id="x",
            reported_changed_files=frozenset(),
            output_text="",
            diagnostics=diag,
            duration_seconds=-1.0,
        )

def test_provider_metadata_immutability():
    diag = ExecutionDiagnostics()
    mutable_meta = {"key": "val"}
    res = ExecutionResult(
        status=ExecutionStatus.COMPLETED,
        provider_id="x",
        reported_changed_files=frozenset(),
        output_text="",
        diagnostics=diag,
        provider_metadata=mutable_meta,
    )
    mutable_meta["key"] = "hacked"
    assert res.provider_metadata["key"] == "val"
    with pytest.raises((TypeError, Exception)):
        res.provider_metadata["new_key"] = 123

def test_fake_provider_protocol():
    class FakeProvider:
        def capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(
                terminal_execution=True,
                network_web=False,
                native_isolation=False,
                filesystem_mutation=True,
                long_running=False,
            )
        def execute(self, request: ExecutionRequest) -> ExecutionResult:
            diag = ExecutionDiagnostics(stdout="Executed fake")
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                provider_id="fake_provider",
                reported_changed_files=frozenset(["fake.py"]),
                output_text="Success",
                diagnostics=diag,
            )
    provider: ExecutionProvider = FakeProvider()
    caps = provider.capabilities()
    assert caps.terminal_execution is True
    req = create_valid_request()
    res = provider.execute(req)
    assert res.status == ExecutionStatus.COMPLETED
    assert res.provider_id == "fake_provider"

def test_no_forbidden_imports():
    import ast
    from pathlib import Path
    forbidden = [
        "adapters.antigravity", "AutonomousRunner",
        "AntigravityCliExecutor", "agy", "codex", "ollama"
    ]
    execution_dir = Path("engine/execution")
    for py_file in execution_dir.glob("**/*.py"):
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for f in forbidden:
                        assert f not in alias.name, f"Forbidden import {f} in {py_file.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                for f in forbidden:
                    assert f not in node.module, f"Forbidden importFrom {f} in {py_file.name}"
