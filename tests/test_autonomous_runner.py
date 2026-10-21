import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adapters.antigravity.autonomous_runner import AutonomousRunner
from adapters.antigravity.models import (
    AntigravityExecutionPlan,
    AntigravityRequest,
    AntigravityResponse,
)
from engine.execution.models import AccessMode
from engine.router.models import RouteDecision


@pytest.fixture(autouse=True)
def mock_sandbox_classes(tmp_path):
    sandbox_path = tmp_path / "_sandbox"
    sandbox_path.mkdir()

    with (
        patch("engine.runner.sandbox.StagingSandbox") as mock_staging,
        patch("engine.runner.sandbox.WorktreeSandbox") as mock_worktree,
    ):
        sandbox_instance = MagicMock()
        sandbox_instance.get_path.return_value = sandbox_path
        mock_staging.return_value = sandbox_instance

        diff_res = MagicMock()
        diff_res.success = True
        diff_res.changes = []
        diff_res.diff_files = []
        sandbox_instance.get_diff.return_value = diff_res

        apply_res = MagicMock()
        apply_res.success = True
        sandbox_instance.apply_to_main.return_value = apply_res

        mock_worktree.return_value = sandbox_instance
        yield sandbox_instance


@pytest.fixture
def mock_adapter(tmp_path):
    adapter = MagicMock()
    adapter.repo_root = tmp_path

    # default load_task_contract — tests that write YAML to disk
    # override this with side_effect per-test
    adapter._load_task_contract.return_value = {
        "status": "approved",
        "approval_status": "approved",
        "acceptance_status": "passed",
    }

    # default plan
    plan = MagicMock(spec=AntigravityExecutionPlan)
    plan.route_decision = RouteDecision(
        workflow_id="implement-task", primary_specialist="harness-maintainer"
    )
    adapter.plan.return_value = plan

    return adapter


@pytest.fixture
def mock_executor():
    executor = MagicMock()
    executor.execute.return_value = AntigravityResponse(raw_text="success")
    return executor


def test_runner_human_gate_awaiting_approval(mock_adapter, mock_executor):
    mock_adapter._load_task_contract.return_value = {
        "status": "awaiting_approval",
        "approval_status": "pending",
    }
    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(project="test", task_id="TASK-0001", user_input="hello")

    trail = runner.run(request)

    assert mock_executor.execute.call_count == 0
    assert len(trail) == 2
    assert trail[0].status == "planned"
    assert trail[1].status == "paused"
    assert "awaiting_approval" in trail[1].reason


def test_runner_human_gate_approval_pending(mock_adapter, mock_executor):
    mock_adapter._load_task_contract.return_value = {
        "status": "approved",
        "approval_status": "pending",
    }
    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(project="test", task_id="TASK-0001", user_input="hello")

    trail = runner.run(request)

    assert mock_executor.execute.call_count == 0
    assert trail[-1].status == "paused"
    assert "pending" in trail[-1].reason


def test_runner_max_steps(mock_adapter, mock_executor):
    """After implement-task → applied, runner pauses with governed review."""
    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(project="test", task_id="TASK-0001", user_input="hello")

    trail = runner.run(request, max_steps=2)

    # Runner exits after step 1 applied → governed review pause
    assert mock_executor.execute.call_count == 1
    assert trail[-1].status == "paused"
    assert "Awaiting governed review" in trail[-1].reason

    # planned, sandbox_created, dispatched, executed, validated, applied, paused
    assert trail[0].status == "planned"
    assert trail[1].status == "sandbox_created"
    assert trail[2].status == "dispatched"
    assert trail[3].status == "executed"
    assert trail[4].status == "validated"
    assert trail[5].status == "applied"
    assert trail[6].status == "paused"


def test_runner_executor_failure(mock_adapter, mock_executor):
    mock_executor.execute.side_effect = Exception("executor crashed")
    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(project="test", task_id="TASK-0001", user_input="hello")

    trail = runner.run(request, max_steps=1)

    assert mock_executor.execute.call_count == 1
    assert trail[0].status == "planned"
    assert trail[1].status == "sandbox_created"
    assert trail[2].status == "dispatched"
    assert trail[3].status == "failed"
    assert "executor crashed" in trail[3].reason


def test_runner_executor_success(mock_adapter, mock_executor):
    """Successful implement-task → applied → paused (governed review)."""
    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(project="test", task_id="TASK-0001", user_input="hello")

    trail = runner.run(request, max_steps=1)

    assert mock_executor.execute.call_count == 1
    assert trail[0].status == "planned"
    assert trail[1].status == "sandbox_created"
    assert trail[2].status == "dispatched"
    assert trail[3].status == "executed"
    assert trail[4].status == "validated"
    assert trail[5].status == "applied"
    assert trail[6].status == "paused"
    assert "Awaiting governed review" in trail[6].reason


def test_runner_human_gate_acceptance_pending(mock_adapter, mock_executor):
    mock_adapter._load_task_contract.return_value = {
        "status": "completed",
        "approval_status": "approved",
        "acceptance_status": "pending",
    }
    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(project="test", task_id="TASK-0001", user_input="hello")

    trail = runner.run(request)

    assert mock_executor.execute.call_count == 0
    assert trail[-1].status == "paused"
    assert "acceptance is pending" in trail[-1].reason


def test_runner_reload_task_contract_dynamic(mock_adapter, mock_executor):
    """
    Tests that resume after approval properly reloads the contract from disk
    and dynamically selects a specialist.
    """
    # 1st call: awaiting_approval
    # 2nd call: approved
    call_count = [0]

    def fake_load(*args):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"status": "awaiting_approval", "approval_status": "pending"}
        return {"status": "approved", "approval_status": "approved"}

    mock_adapter._load_task_contract.side_effect = fake_load

    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(project="test", task_id="TASK-0001", user_input="implement")

    # First run -> pauses immediately
    trail1 = runner.run(request, max_steps=1)
    assert trail1[-1].status == "paused"

    # Human approves here...

    # Second run (resume) -> re-reads from disk (which returns approved now), plans, executes
    trail2 = runner.run(request, max_steps=1)
    assert trail2[0].status == "planned"
    assert trail2[1].status == "sandbox_created"
    assert trail2[2].status == "dispatched"
    assert trail2[3].status == "executed"
    assert trail2[4].status == "validated"
    assert trail2[5].status == "applied"

    # Proof it loaded from disk
    assert mock_adapter._load_task_contract.call_count >= 2
    # Proof it executed the new plan instead of blindly reusing the old one
    assert mock_adapter.plan.call_count == 2


def test_runner_escalation_pause(mock_adapter, mock_executor):
    """discuss workflow with escalation intent → paused by human gate."""
    plan = MagicMock(spec=AntigravityExecutionPlan)
    plan.route_decision = RouteDecision(workflow_id="discuss", primary_specialist="general-advisor")
    mock_adapter.plan.return_value = plan

    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(
        project="test", task_id="TASK-0001", user_input="Escalation required. missing."
    )

    trail = runner.run(request)

    assert trail[-1].status == "paused"
    # Human gate fires first (before workflow mode check)
    assert "Escalation" in trail[-1].reason
    assert mock_executor.execute.call_count == 0


def test_audit_trail_real_file_persistence(mock_adapter, mock_executor, tmp_path):
    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(project="test", task_id="TASK-0001", user_input="hello")

    runner.run(request, max_steps=1)

    evidence_file = tmp_path / "projects" / "test" / "evidence" / "TASK-0001" / "audit_trail.jsonl"
    assert evidence_file.exists()

    lines = evidence_file.read_text().strip().split("\n")
    # planned, sandbox_created, dispatched, executed, validated, applied, paused(governed)
    assert len(lines) == 7

    j0 = json.loads(lines[0])
    assert j0["status"] == "planned"

    j1 = json.loads(lines[1])
    assert j1["status"] == "sandbox_created"
    j2 = json.loads(lines[2])
    assert j2["status"] == "dispatched"

    j3 = json.loads(lines[3])
    assert j3["status"] == "executed"

    j6 = json.loads(lines[6])
    assert j6["status"] == "paused"
    assert "Awaiting governed review" in j6["reason"]


# --- Helper to build a valid contract dict for the new tests ---
def _make_contract(task_id, modify_paths):
    return {
        "task_id": task_id,
        "task_type": "standard",
        "title": f"Test {task_id}",
        "description": f"Contract for {task_id}",
        "project": "test",
        "status": "approved",
        "approval_status": "approved",
        "approved_by": "test-user",
        "approved_at": "2026-08-30T20:00:00Z",
        "approval_source": "test",
        "approval_session_id": "test-session",
        "approval_receipt": "test-receipt",
        "acceptance_status": "pending",
        "accepted_by": None,
        "accepted_at": None,
        "deviation": {
            "documented": False,
            "reason": None,
            "authorized_by": None,
            "mitigation_plan": None,
        },
        "implementation_baseline": {
            "git_head": None,
            "working_tree_clean": None,
            "captured_at": None,
            "preexisting_untracked": [],
        },
        "scope": {
            "planned_paths": {
                "modify": modify_paths,
                "read": [],
            },
            "allowed_actions": {"terminal": [], "web": []},
            "forbidden_actions": [],
        },
        "assigned_workflow": "implement-task",
        "assigned_specialists": ["frontend-engineer"],
        "evidence": {
            "tests": {"status": None},
            "code_review": {"status": None},
            "security_review": {"status": None},
        },
        "postcheck": {"status": None, "run_at": None, "findings": []},
        "approval_history": [],
        "acceptance_history": [],
        "created_at": "2026-08-30T20:00:00Z",
        "updated_at": "2026-08-30T20:00:00Z",
        "acceptance_criteria": [],
    }


def _write_contract(adapter, task_id, modify_paths):
    """Write contract YAML and wire _load_task_contract to read it."""
    import yaml

    contract = _make_contract(task_id, modify_paths)
    task_file = adapter.repo_root / "projects" / "test" / "tasks" / f"{task_id}.yaml"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(yaml.dump(contract, default_flow_style=False))

    def load_from_disk(project, tid):
        path = adapter.repo_root / "projects" / project / "tasks" / f"{tid}.yaml"
        if path.exists():
            return yaml.safe_load(path.read_text())
        return {"status": "approved", "approval_status": "approved"}

    adapter._load_task_contract.side_effect = load_from_disk
    return contract


def test_validation_fails_empty_diff(mock_adapter, mock_executor, mock_sandbox_classes):
    """Empty diff when modifications expected → production rejects → NOT validated."""
    _write_contract(mock_adapter, "TASK-9000", ["some_file.txt"])

    # Sandbox returns success but empty diff (agy created nothing)
    diff_res = MagicMock()
    diff_res.success = True
    diff_res.changes = []
    diff_res.diff_files = []
    mock_sandbox_classes.get_diff.return_value = diff_res

    runner = AutonomousRunner(mock_adapter, mock_executor)
    req = AntigravityRequest(project="test", user_input="implement", task_id="TASK-9000")

    trail = runner.run(req, max_steps=1)

    statuses = [e.status for e in trail]
    assert "failed" in statuses
    assert "validated" not in statuses
    assert "applied" not in statuses
    assert "executed" in statuses
    failed_entry = next(e for e in trail if e.status == "failed")
    assert "Empty diff" in failed_entry.reason


def test_apply_fails_if_file_missing(mock_adapter, mock_executor, mock_sandbox_classes):
    """Diff reports file but apply fails physically → NOT applied."""
    from engine.runner.sandbox import SandboxChange

    _write_contract(mock_adapter, "TASK-9001", ["missing.txt"])

    # get_diff reports the file was touched
    diff_res = MagicMock()
    diff_res.success = True
    diff_res.changes = [SandboxChange(status="M", path="missing.txt")]
    diff_res.diff_files = ["missing.txt"]
    mock_sandbox_classes.get_diff.return_value = diff_res

    # apply_to_main fails (file doesn't physically exist)
    apply_res = MagicMock()
    apply_res.success = False
    apply_res.error = "File missing.txt not in sandbox or main repo"
    mock_sandbox_classes.apply_to_main.return_value = apply_res

    runner = AutonomousRunner(mock_adapter, mock_executor)
    req = AntigravityRequest(project="test", user_input="implement", task_id="TASK-9001")

    trail = runner.run(req, max_steps=1)

    statuses = [e.status for e in trail]
    assert "validated" in statuses
    assert "failed" in statuses
    assert "applied" not in statuses


def test_scope_violation_out_of_scope_file(mock_adapter, mock_executor, mock_sandbox_classes):
    """Diff contains file not in scope → NOT validated → NOT applied."""
    from engine.runner.sandbox import SandboxChange

    _write_contract(mock_adapter, "TASK-9003", ["allowed.txt"])

    diff_res = MagicMock()
    diff_res.success = True
    diff_res.changes = [
        SandboxChange(status="M", path="allowed.txt"),
        SandboxChange(status="A", path="rogue.txt"),
    ]
    diff_res.diff_files = ["allowed.txt", "rogue.txt"]
    mock_sandbox_classes.get_diff.return_value = diff_res

    runner = AutonomousRunner(mock_adapter, mock_executor)
    req = AntigravityRequest(project="test", user_input="implement", task_id="TASK-9003")

    trail = runner.run(req, max_steps=1)

    statuses = [e.status for e in trail]
    assert "failed" in statuses
    assert "validated" not in statuses
    assert "applied" not in statuses
    failed_entry = next(e for e in trail if e.status == "failed")
    assert "Out-of-scope" in failed_entry.reason
    assert "rogue.txt" in failed_entry.reason


def test_untracked_contract_propagated_to_worktree(
    mock_adapter, mock_executor, mock_sandbox_classes
):
    """Untracked contract in main → Harness copies to sandbox → executor sees it."""
    import yaml

    _write_contract(mock_adapter, "TASK-9002", [])

    captured = {}

    def capturing_execute(plan, sandbox_dir=None):
        captured["sandbox_dir"] = sandbox_dir
        return AntigravityResponse(raw_text="success")

    mock_executor.execute.side_effect = capturing_execute

    runner = AutonomousRunner(mock_adapter, mock_executor)
    req = AntigravityRequest(project="test", user_input="implement", task_id="TASK-9002")

    runner.run(req, max_steps=1)

    sandbox_dir = captured.get("sandbox_dir")
    assert sandbox_dir is not None, "executor must receive sandbox_dir"
    assert isinstance(sandbox_dir, Path)

    sandbox_task = sandbox_dir / "projects" / "test" / "tasks" / "TASK-9002.yaml"
    assert sandbox_task.exists(), "Contract must be propagated to worktree"
    data = yaml.safe_load(sandbox_task.read_text())
    assert data["status"] == "approved"
    assert data["task_id"] == "TASK-9002"


def test_rename_out_of_scope_rejected(mock_adapter, mock_executor, mock_sandbox_classes):
    """R old.py -> rogue.py where rogue.py not in scope → NOT validated."""
    from engine.runner.sandbox import SandboxChange

    _write_contract(mock_adapter, "TASK-9004", ["old.py"])

    diff_res = MagicMock()
    diff_res.success = True
    diff_res.changes = [
        SandboxChange(status="R", path="rogue.py", old_path="old.py"),
    ]
    diff_res.diff_files = ["rogue.py"]
    mock_sandbox_classes.get_diff.return_value = diff_res

    runner = AutonomousRunner(mock_adapter, mock_executor)
    req = AntigravityRequest(project="test", user_input="implement", task_id="TASK-9004")

    trail = runner.run(req, max_steps=1)

    statuses = [e.status for e in trail]
    assert "failed" in statuses
    assert "validated" not in statuses
    assert "applied" not in statuses
    failed_entry = next(e for e in trail if e.status == "failed")
    assert "Out-of-scope" in failed_entry.reason
    assert "rogue.py" in failed_entry.reason


# --- New tests for HARNESS-0021 fixes ---


def test_discuss_never_produces_applied(mock_adapter, mock_executor):
    """discuss workflow → paused immediately, no sandbox, no executor, no applied."""
    plan = MagicMock(spec=AntigravityExecutionPlan)
    plan.route_decision = RouteDecision(workflow_id="discuss", primary_specialist="general-advisor")
    mock_adapter.plan.return_value = plan

    runner = AutonomousRunner(mock_adapter, mock_executor)
    req = AntigravityRequest(
        project="test", task_id="TASK-0001", user_input="tell me about this code"
    )

    trail = runner.run(req, max_steps=3)

    statuses = [e.status for e in trail]
    assert "planned" in statuses
    assert "paused" in statuses
    assert "sandbox_created" not in statuses
    assert "dispatched" not in statuses
    assert "executed" not in statuses
    assert "validated" not in statuses
    assert "applied" not in statuses

    assert mock_executor.execute.call_count == 0

    paused_entry = next(e for e in trail if e.status == "paused")
    assert "not enabled" in paused_entry.reason
    assert "discuss" in paused_entry.reason


def test_implement_applied_then_governed_pause(mock_adapter, mock_executor, mock_sandbox_classes):
    """implement-task → applied → paused (governed review). No Step 2 discuss."""
    runner = AutonomousRunner(mock_adapter, mock_executor)
    req = AntigravityRequest(project="test", task_id="TASK-0001", user_input="implement this")

    trail = runner.run(req, max_steps=5)

    statuses = [e.status for e in trail]

    # Must have the complete implementation lifecycle
    assert statuses == [
        "planned",
        "sandbox_created",
        "dispatched",
        "executed",
        "validated",
        "applied",
        "paused",
    ]

    # Paused by governed review, NOT max_steps
    assert "Awaiting governed review" in trail[-1].reason
    assert "max_steps" not in trail[-1].reason

    # Executor called exactly once — no second iteration
    assert mock_executor.execute.call_count == 1

    # adapter.plan called exactly once — no second routing to discuss
    assert mock_adapter.plan.call_count == 1

    # No discuss workflow anywhere
    workflows = [e.workflow for e in trail if e.workflow]
    assert "discuss" not in workflows


# --- Tests for Task Artifact Materialization (HARNESS-BOOTSTRAP-0002) ---


def test_materialize_both_task_and_proposal(mock_adapter, mock_executor, mock_sandbox_classes):
    """Both task and proposal exist -> both copied to sandbox."""
    import yaml

    _write_contract(mock_adapter, "TASK-1001", [])
    proposal_file = mock_adapter.repo_root / "projects" / "test" / "proposals" / "TASK-1001.md"
    proposal_file.parent.mkdir(parents=True, exist_ok=True)
    proposal_file.write_text("# Proposal for TASK-1001", encoding="utf-8")

    captured = {}

    def capturing_execute(plan, sandbox_dir=None):
        captured["sandbox_dir"] = sandbox_dir
        return AntigravityResponse(raw_text="success")

    mock_executor.execute.side_effect = capturing_execute

    runner = AutonomousRunner(mock_adapter, mock_executor)
    req = AntigravityRequest(project="test", user_input="implement", task_id="TASK-1001")

    runner.run(req, max_steps=1)

    sandbox_dir = captured.get("sandbox_dir")
    assert sandbox_dir is not None

    sandbox_task = sandbox_dir / "projects" / "test" / "tasks" / "TASK-1001.yaml"
    sandbox_proposal = sandbox_dir / "projects" / "test" / "proposals" / "TASK-1001.md"

    assert sandbox_task.exists()
    data = yaml.safe_load(sandbox_task.read_text())
    assert data["task_id"] == "TASK-1001"

    assert sandbox_proposal.exists()
    assert sandbox_proposal.read_text(encoding="utf-8") == "# Proposal for TASK-1001"


def test_materialize_task_exists_proposal_absent(mock_adapter, mock_executor, mock_sandbox_classes):
    """Task exists, proposal absent -> only task copied, no error."""
    import yaml

    _write_contract(mock_adapter, "TASK-1002", [])

    captured = {}

    def capturing_execute(plan, sandbox_dir=None):
        captured["sandbox_dir"] = sandbox_dir
        return AntigravityResponse(raw_text="success")

    mock_executor.execute.side_effect = capturing_execute

    runner = AutonomousRunner(mock_adapter, mock_executor)
    req = AntigravityRequest(project="test", user_input="implement", task_id="TASK-1002")

    trail = runner.run(req, max_steps=1)

    # Verify execution succeeded without error
    statuses = [e.status for e in trail]
    assert "failed" not in statuses

    sandbox_dir = captured.get("sandbox_dir")
    assert sandbox_dir is not None

    sandbox_task = sandbox_dir / "projects" / "test" / "tasks" / "TASK-1002.yaml"
    sandbox_proposal = sandbox_dir / "projects" / "test" / "proposals" / "TASK-1002.md"

    assert sandbox_task.exists()
    data = yaml.safe_load(sandbox_task.read_text())
    assert data["task_id"] == "TASK-1002"

    assert not sandbox_proposal.exists()


def test_materialize_other_task_and_proposal_not_copied(
    mock_adapter, mock_executor, mock_sandbox_classes
):
    """Other task/proposal -> not copied."""
    _write_contract(mock_adapter, "TASK-1001", [])
    prop1 = mock_adapter.repo_root / "projects" / "test" / "proposals" / "TASK-1001.md"
    prop1.parent.mkdir(parents=True, exist_ok=True)
    prop1.write_text("# Proposal 1", encoding="utf-8")

    # Other task and proposal
    task2 = mock_adapter.repo_root / "projects" / "test" / "tasks" / "TASK-1002.yaml"
    task2.write_text("task_id: TASK-1002\n", encoding="utf-8")
    prop2 = mock_adapter.repo_root / "projects" / "test" / "proposals" / "TASK-1002.md"
    prop2.write_text("# Proposal 2", encoding="utf-8")

    captured = {}

    def capturing_execute(plan, sandbox_dir=None):
        captured["sandbox_dir"] = sandbox_dir
        return AntigravityResponse(raw_text="success")

    mock_executor.execute.side_effect = capturing_execute

    runner = AutonomousRunner(mock_adapter, mock_executor)
    req = AntigravityRequest(project="test", user_input="implement", task_id="TASK-1001")

    runner.run(req, max_steps=1)

    sandbox_dir = captured.get("sandbox_dir")
    assert sandbox_dir is not None

    # Current task/proposal materialized
    assert (sandbox_dir / "projects" / "test" / "tasks" / "TASK-1001.yaml").exists()
    assert (sandbox_dir / "projects" / "test" / "proposals" / "TASK-1001.md").exists()

    # Other task/proposal NOT materialized
    assert not (sandbox_dir / "projects" / "test" / "tasks" / "TASK-1002.yaml").exists()
    assert not (sandbox_dir / "projects" / "test" / "proposals" / "TASK-1002.md").exists()


def test_materialize_path_traversal_injection(mock_adapter, mock_executor, tmp_path):
    """Path traversal injection -> ValueError."""
    runner = AutonomousRunner(mock_adapter, mock_executor)
    sandbox_path = tmp_path / "sandbox"
    sandbox_path.mkdir()

    # Invalid project formats / traversal
    with pytest.raises(ValueError, match="Invalid project"):
        runner._materialize_task_artifacts(
            sandbox_path,
            AntigravityRequest(project="../escaped", task_id="TASK-1001", user_input="test"),
        )

    with pytest.raises(ValueError, match="Invalid project"):
        runner._materialize_task_artifacts(
            sandbox_path,
            AntigravityRequest(project="test/sub", task_id="TASK-1001", user_input="test"),
        )

    # Invalid task_id formats / traversal
    with pytest.raises(ValueError, match="Invalid task_id"):
        runner._materialize_task_artifacts(
            sandbox_path,
            AntigravityRequest(project="test", task_id="../EVIL-1001", user_input="test"),
        )

    with pytest.raises(ValueError, match="Invalid task_id"):
        runner._materialize_task_artifacts(
            sandbox_path,
            AntigravityRequest(project="test", task_id="TASK-1001/../OTHER", user_input="test"),
        )

    with pytest.raises(ValueError, match="Invalid task_id"):
        runner._materialize_task_artifacts(
            sandbox_path,
            AntigravityRequest(project="test", task_id="task-lower", user_input="test"),
        )

    with pytest.raises(ValueError, match="Invalid task_id"):
        runner._materialize_task_artifacts(
            sandbox_path,
            AntigravityRequest(project="test", task_id="TASK$1001", user_input="test"),
        )


def test_materialize_arbitrary_untracked_files_not_copied(
    mock_adapter, mock_executor, mock_sandbox_classes
):
    """Arbitrary untracked files (e.g. specialists, dirty files) -> not copied."""
    _write_contract(mock_adapter, "TASK-1001", [])

    # Create arbitrary untracked files in the repo root
    specialist_file = (
        mock_adapter.repo_root / "core" / "specialists" / "rogue-specialist" / "prompt.md"
    )
    specialist_file.parent.mkdir(parents=True, exist_ok=True)
    specialist_file.write_text("rogue specialist", encoding="utf-8")

    dirty_file = mock_adapter.repo_root / "dirty_script.py"
    dirty_file.write_text("print('dirty')", encoding="utf-8")

    extra_project_file = mock_adapter.repo_root / "projects" / "test" / "extra.txt"
    extra_project_file.write_text("extra", encoding="utf-8")

    captured = {}

    def capturing_execute(plan, sandbox_dir=None):
        captured["sandbox_dir"] = sandbox_dir
        return AntigravityResponse(raw_text="success")

    mock_executor.execute.side_effect = capturing_execute

    runner = AutonomousRunner(mock_adapter, mock_executor)
    req = AntigravityRequest(project="test", user_input="implement", task_id="TASK-1001")

    runner.run(req, max_steps=1)

    sandbox_dir = captured.get("sandbox_dir")
    assert sandbox_dir is not None

    # Only the current task contract was materialized
    assert (sandbox_dir / "projects" / "test" / "tasks" / "TASK-1001.yaml").exists()

    # Untracked files were NOT copied
    assert not (sandbox_dir / "core" / "specialists" / "rogue-specialist" / "prompt.md").exists()
    assert not (sandbox_dir / "dirty_script.py").exists()
    assert not (sandbox_dir / "projects" / "test" / "extra.txt").exists()


def test_materialize_harness_internal_fallback(mock_adapter, mock_executor, mock_sandbox_classes):
    """Artifacts in .harness-internal are materialized when requested project has none."""
    task_file = (
        mock_adapter.repo_root
        / "projects"
        / ".harness-internal"
        / "tasks"
        / "HARNESS-BOOTSTRAP-0002.yaml"
    )
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("task_id: HARNESS-BOOTSTRAP-0002\nstatus: approved\n", encoding="utf-8")

    prop_file = (
        mock_adapter.repo_root
        / "projects"
        / ".harness-internal"
        / "proposals"
        / "HARNESS-BOOTSTRAP-0002.md"
    )
    prop_file.parent.mkdir(parents=True, exist_ok=True)
    prop_file.write_text("# Proposal HARNESS-BOOTSTRAP-0002\n", encoding="utf-8")

    captured = {}

    def capturing_execute(plan, sandbox_dir=None):
        captured["sandbox_dir"] = sandbox_dir
        return AntigravityResponse(raw_text="success")

    mock_executor.execute.side_effect = capturing_execute

    runner = AutonomousRunner(mock_adapter, mock_executor)
    req = AntigravityRequest(
        project="other-project", user_input="implement", task_id="HARNESS-BOOTSTRAP-0002"
    )

    runner.run(req, max_steps=1)

    sandbox_dir = captured.get("sandbox_dir")
    assert sandbox_dir is not None

    assert (
        sandbox_dir / "projects" / ".harness-internal" / "tasks" / "HARNESS-BOOTSTRAP-0002.yaml"
    ).exists()
    assert (
        sandbox_dir / "projects" / ".harness-internal" / "proposals" / "HARNESS-BOOTSTRAP-0002.md"
    ).exists()


def test_runner_modify_paths_deny_all(mock_adapter, mock_executor, monkeypatch):
    """A request with DENY_ALL prevents any modifications even if legacy allows it."""
    plan = MagicMock()
    plan.route_decision = RouteDecision(
        workflow_id="implement-task", primary_specialist="Harness Evolution Advisor"
    )
    mock_adapter.plan.return_value = plan

    mock_adapter._load_task_contract.return_value = {
        "status": "approved",
        "approval_status": "approved",
        "scope": {"planned_paths": {"modify": ["src/a.py"]}},
    }

    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(
        project="test",
        task_id="TASK-0001",
        user_input="hello",
        modify_paths_mode=AccessMode.DENY_ALL,
    )

    class FakeChange:
        def __init__(self, path, old_path):
            self.path = path
            self.old_path = old_path

    class FakeDiff:
        success = True
        changes = [FakeChange("src/a.py", None)]

    class FakeSandbox:
        sandbox_dir = Path("/fake")

        def setup(self):
            pass

        def get_path(self):
            return self.sandbox_dir

        def get_diff(self, *args, **kwargs):
            return FakeDiff()

        def cleanup(self):
            pass

        def apply_to_main(self, *args, **kwargs):
            return type("AR", (), {"success": True, "error": None})()

    import engine.runner.sandbox

    monkeypatch.setattr(
        engine.runner.sandbox, "WorktreeSandbox", lambda *args, **kwargs: FakeSandbox()
    )

    outcome = runner.run_execution(request, max_steps=1)

    assert outcome.failure_kind == "governance"
    assert "Out-of-scope files" in outcome.trail[-1].reason
    assert "src/a.py" in outcome.trail[-1].reason


def test_runner_modify_paths_allow_list(mock_adapter, mock_executor, monkeypatch):
    """
    A request with ALLOW_LIST prevents modifications to files not in the list
    even if legacy allows them.
    """
    plan = MagicMock()
    plan.route_decision = RouteDecision(
        workflow_id="implement-task", primary_specialist="Harness Evolution Advisor"
    )
    mock_adapter.plan.return_value = plan

    mock_adapter._load_task_contract.return_value = {
        "status": "approved",
        "approval_status": "approved",
        "scope": {"planned_paths": {"modify": ["src/a.py", "src/b.py"]}},
    }

    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(
        project="test",
        task_id="TASK-0001",
        user_input="hello",
        modify_paths_mode=AccessMode.ALLOW_LIST,
        modify_paths_values=frozenset(["src/a.py"]),
    )

    class FakeChange:
        def __init__(self, path, old_path):
            self.path = path
            self.old_path = old_path

    class FakeDiff:
        success = True
        changes = [FakeChange("src/b.py", None)]

    class FakeSandbox:
        sandbox_dir = Path("/fake")

        def setup(self):
            pass

        def get_path(self):
            return self.sandbox_dir

        def get_diff(self, *args, **kwargs):
            return FakeDiff()

        def cleanup(self):
            pass

        def apply_to_main(self, *args, **kwargs):
            return type("AR", (), {"success": True, "error": None})()

    import engine.runner.sandbox

    monkeypatch.setattr(
        engine.runner.sandbox, "WorktreeSandbox", lambda *args, **kwargs: FakeSandbox()
    )

    outcome = runner.run_execution(request, max_steps=1)

    assert outcome.failure_kind == "governance"
    assert "src/b.py" in outcome.trail[-1].reason


def test_runner_modify_paths_allow_list_success(mock_adapter, mock_executor, monkeypatch):
    """A request with ALLOW_LIST succeeds if the file is in both legacy and request lists."""
    plan = MagicMock()
    plan.route_decision = RouteDecision(
        workflow_id="implement-task", primary_specialist="Harness Evolution Advisor"
    )
    mock_adapter.plan.return_value = plan

    mock_adapter._load_task_contract.return_value = {
        "status": "approved",
        "approval_status": "approved",
        "scope": {"planned_paths": {"modify": ["src/a.py", "src/b.py"]}},
    }

    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(
        project="test",
        task_id="TASK-0001",
        user_input="hello",
        modify_paths_mode=AccessMode.ALLOW_LIST,
        modify_paths_values=frozenset(["src/a.py"]),
    )

    class FakeChange:
        def __init__(self, path, old_path):
            self.path = path
            self.old_path = old_path

    class FakeDiff:
        success = True
        changes = [FakeChange("src/a.py", None)]

    class FakeSandbox:
        sandbox_dir = Path("/fake")

        def setup(self):
            pass

        def get_path(self):
            return self.sandbox_dir

        def get_diff(self, *args, **kwargs):
            return FakeDiff()

        def cleanup(self):
            pass

        def apply_to_main(self, *args, **kwargs):
            return type("AR", (), {"success": True, "error": None})()

    import engine.runner.sandbox

    monkeypatch.setattr(
        engine.runner.sandbox, "WorktreeSandbox", lambda *args, **kwargs: FakeSandbox()
    )

    outcome = runner.run_execution(request, max_steps=1)

    assert outcome.failure_kind is None
    assert "src/a.py" in outcome.observed_changed_files


def test_runner_modify_paths_unrestricted(mock_adapter, mock_executor, monkeypatch):
    """A request with UNRESTRICTED is still limited by the legacy contract."""
    plan = MagicMock()
    plan.route_decision = RouteDecision(
        workflow_id="implement-task", primary_specialist="Harness Evolution Advisor"
    )
    mock_adapter.plan.return_value = plan

    mock_adapter._load_task_contract.return_value = {
        "status": "approved",
        "approval_status": "approved",
        "scope": {"planned_paths": {"modify": ["src/a.py"]}},
    }

    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(
        project="test",
        task_id="TASK-0001",
        user_input="hello",
        modify_paths_mode=AccessMode.UNRESTRICTED,
    )

    class FakeChange:
        def __init__(self, path, old_path):
            self.path = path
            self.old_path = old_path

    class FakeDiff:
        success = True
        changes = [FakeChange("src/b.py", None)]

    class FakeSandbox:
        sandbox_dir = Path("/fake")

        def setup(self):
            pass

        def get_path(self):
            return self.sandbox_dir

        def get_diff(self, *args, **kwargs):
            return FakeDiff()

        def cleanup(self):
            pass

        def apply_to_main(self, *args, **kwargs):
            return type("AR", (), {"success": True, "error": None})()

    import engine.runner.sandbox

    monkeypatch.setattr(
        engine.runner.sandbox, "WorktreeSandbox", lambda *args, **kwargs: FakeSandbox()
    )

    outcome = runner.run_execution(request, max_steps=1)

    assert outcome.failure_kind == "governance"
    assert "src/b.py" in outcome.trail[-1].reason


def test_runner_rename_governance(mock_adapter, mock_executor, monkeypatch):
    """A rename where old_path is valid but path is invalid fails."""
    plan = MagicMock()
    plan.route_decision = RouteDecision(
        workflow_id="implement-task", primary_specialist="Harness Evolution Advisor"
    )
    mock_adapter.plan.return_value = plan

    mock_adapter._load_task_contract.return_value = {
        "status": "approved",
        "approval_status": "approved",
        "scope": {"planned_paths": {"modify": ["src/old.py"]}},
    }

    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(project="test", task_id="TASK-0001", user_input="hello")

    class FakeChange:
        def __init__(self, path, old_path):
            self.path = path
            self.old_path = old_path

    class FakeDiff:
        success = True
        changes = [FakeChange("src/new.py", "src/old.py")]

    class FakeSandbox:
        sandbox_dir = Path("/fake")

        def setup(self):
            pass

        def get_path(self):
            return self.sandbox_dir

        def get_diff(self, *args, **kwargs):
            return FakeDiff()

        def cleanup(self):
            pass

        def apply_to_main(self, *args, **kwargs):
            return type("AR", (), {"success": True, "error": None})()

    import engine.runner.sandbox

    monkeypatch.setattr(
        engine.runner.sandbox, "WorktreeSandbox", lambda *args, **kwargs: FakeSandbox()
    )

    outcome = runner.run_execution(request, max_steps=1)

    assert outcome.failure_kind == "governance"
    assert "src/new.py" in outcome.trail[-1].reason


def test_autonomous_runner_set_dict_regression(mock_adapter, mock_executor, monkeypatch):
    from pathlib import Path
    from unittest.mock import MagicMock

    from adapters.antigravity.autonomous_runner import AutonomousRunner
    from adapters.antigravity.models import AntigravityRequest, RouteDecision

    plan = MagicMock()
    plan.route_decision = RouteDecision(
        workflow_id="implement-task", primary_specialist="Harness Evolution Advisor"
    )
    mock_adapter.plan.return_value = plan

    mock_adapter._load_task_contract.return_value = {
        "status": "approved",
        "approval_status": "approved",
        "scope": {"planned_paths": {"modify": {"mode": "allow_list", "values": ["src/a.py"]}}},
    }

    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(
        project="test",
        task_id="TASK-0001",
        user_input="hello",
        modify_paths_mode=AccessMode.ALLOW_LIST,
        modify_paths_values=frozenset(["src/a.py"]),
    )

    class FakeChange:
        def __init__(self, path, old_path):
            self.path = path
            self.old_path = old_path

    class FakeDiff:
        success = True
        changes = [FakeChange("src/a.py", None)]

    class FakeSandbox:
        sandbox_dir = Path("/fake")

        def setup(self):
            pass

        def get_path(self):
            return self.sandbox_dir

        def get_diff(self, *args, **kwargs):
            return FakeDiff()

        def cleanup(self):
            pass

        def apply_to_main(self, *args, **kwargs):
            return type("AR", (), {"success": True, "error": None})()

    import engine.runner.sandbox

    monkeypatch.setattr(
        engine.runner.sandbox, "WorktreeSandbox", lambda *args, **kwargs: FakeSandbox()
    )

    outcome = runner.run_execution(request, max_steps=1)
    # the dictionary must not be interpreted as {"mode", "values"} which would reject src/a.py
    assert outcome.failure_kind is None


def test_autonomous_runner_and_semantics(mock_adapter, mock_executor, monkeypatch):
    from pathlib import Path
    from unittest.mock import MagicMock

    from adapters.antigravity.autonomous_runner import AutonomousRunner
    from adapters.antigravity.models import AntigravityRequest, RouteDecision

    plan = MagicMock()
    plan.route_decision = RouteDecision(
        workflow_id="implement-task", primary_specialist="Harness Evolution Advisor"
    )
    mock_adapter.plan.return_value = plan

    mock_adapter._load_task_contract.return_value = {
        "status": "approved",
        "approval_status": "approved",
        "scope": {"planned_paths": {"modify": {"mode": "unrestricted"}}},
    }

    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(
        project="test",
        task_id="TASK-0001",
        user_input="hello",
        modify_paths_mode=AccessMode.ALLOW_LIST,
        modify_paths_values=frozenset(["src/a.py"]),
    )

    class FakeChange:
        def __init__(self, path, old_path):
            self.path = path
            self.old_path = old_path

    class FakeDiff:
        success = True
        changes = [FakeChange("src/a.py", None), FakeChange("src/b.py", None)]

    class FakeSandbox:
        sandbox_dir = Path("/fake")

        def setup(self):
            pass

        def get_path(self):
            return self.sandbox_dir

        def get_diff(self, *args, **kwargs):
            return FakeDiff()

        def cleanup(self):
            pass

        def apply_to_main(self, *args, **kwargs):
            return type("AR", (), {"success": True, "error": None})()

    import engine.runner.sandbox

    monkeypatch.setattr(
        engine.runner.sandbox, "WorktreeSandbox", lambda *args, **kwargs: FakeSandbox()
    )

    outcome = runner.run_execution(request, max_steps=1)
    assert outcome.failure_kind == "governance"


def test_autonomous_runner_deny_all_semantics(mock_adapter, mock_executor, monkeypatch):
    from pathlib import Path
    from unittest.mock import MagicMock

    from adapters.antigravity.autonomous_runner import AutonomousRunner
    from adapters.antigravity.models import AntigravityRequest, RouteDecision

    plan = MagicMock()
    plan.route_decision = RouteDecision(
        workflow_id="implement-task", primary_specialist="Harness Evolution Advisor"
    )
    mock_adapter.plan.return_value = plan

    mock_adapter._load_task_contract.return_value = {
        "status": "approved",
        "approval_status": "approved",
        "scope": {"planned_paths": {"modify": {"mode": "deny_all"}}},
    }

    runner = AutonomousRunner(mock_adapter, mock_executor)
    request = AntigravityRequest(
        project="test",
        task_id="TASK-0001",
        user_input="hello",
        modify_paths_mode=AccessMode.UNRESTRICTED,
    )

    class FakeChange:
        def __init__(self, path, old_path):
            self.path = path
            self.old_path = old_path

    class FakeDiff:
        success = True
        changes = [FakeChange("src/a.py", None)]

    class FakeSandbox:
        sandbox_dir = Path("/fake")

        def setup(self):
            pass

        def get_path(self):
            return self.sandbox_dir

        def get_diff(self, *args, **kwargs):
            return FakeDiff()

        def cleanup(self):
            pass

        def apply_to_main(self, *args, **kwargs):
            return type("AR", (), {"success": True, "error": None})()

    import engine.runner.sandbox

    monkeypatch.setattr(
        engine.runner.sandbox, "WorktreeSandbox", lambda *args, **kwargs: FakeSandbox()
    )

    outcome = runner.run_execution(request, max_steps=1)
    assert outcome.failure_kind == "governance"
