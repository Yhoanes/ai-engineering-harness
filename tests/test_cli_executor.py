import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from adapters.antigravity.cli_executor import AntigravityCliExecutor, _truncate_diagnostic
from adapters.antigravity.models import AntigravityExecutionPlan
from engine.orchestrator.models import OrchestratorHandoff
from engine.router.models import RouteDecision


@pytest.fixture
def plan():
    decision = RouteDecision(
        workflow_id="implement-task",
        primary_specialist="harness-maintainer"
    )
    handoff = OrchestratorHandoff(
        project="_harness-internal",
        workflow="implement-task",
        primary_specialist="harness-maintainer",
    )
    return AntigravityExecutionPlan(
        route_decision=decision,
        orchestrator_handoff=handoff,
        specialist_prompt="sys",
        workflow_prompt="wf",
        context_payload="ctx",
        restrictions=[],
        expected_output_contract=[],
        final_prompt="Do something"
    )


def test_truncate_diagnostic():
    # 6. Enormous stderr => deterministically truncated
    assert _truncate_diagnostic(None) == ""
    assert _truncate_diagnostic("short") == "short"
    assert _truncate_diagnostic("x" * 8193).endswith("... (truncated)")
    assert len(_truncate_diagnostic("x" * 8193)) == 8192 + len("... (truncated)")


def test_cli_success(plan, tmp_path):
    # 1. SUCCESS + valid non-empty response => success
    # 12. metadata securely preserves status, num_turns, usage, duration, returncode
    # 13. Regression tests for existing executor mocks
    executor = AntigravityCliExecutor()
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stderr = ""
    mock_res.stdout = json.dumps(
        {
            "status": "SUCCESS",
            "response": "done",
            "conversation_id": "123",
            "num_turns": 2,
            "duration_seconds": 10.5,
            "usage": {"in": 1, "out": 2}
        }
    )

    with patch("subprocess.run", return_value=mock_res):
        resp = executor.execute(plan, tmp_path)

        assert resp.raw_text == "done"
        assert resp.metadata["conversation_id"] == "123"
        assert resp.metadata["status"] == "SUCCESS"
        assert resp.metadata["num_turns"] == 2
        assert resp.metadata["duration_seconds"] == 10.5
        assert resp.metadata["usage"] == {"in": 1, "out": 2}
        assert resp.metadata["returncode"] == 0
        assert resp.metadata["stderr"] == ""


def test_cli_success_with_stderr(plan, tmp_path):
    # 5. stderr + valid response => success + bounded stderr in metadata
    executor = AntigravityCliExecutor()
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stderr = "warning: something"
    mock_res.stdout = json.dumps(
        {"status": "SUCCESS", "response": "done"}
    )

    with patch("subprocess.run", return_value=mock_res):
        resp = executor.execute(plan, tmp_path)

        assert resp.raw_text == "done"
        assert resp.metadata["stderr"] == "warning: something"
        assert resp.metadata["returncode"] == 0


def test_cli_success_empty_response(plan, tmp_path):
    # 2. SUCCESS + "" => failure
    # 7. stderr + empty response => error message contains bounded stderr
    executor = AntigravityCliExecutor()
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stderr = "agent hit max iterations"
    mock_res.stdout = json.dumps(
        {"status": "SUCCESS", "response": ""}
    )

    with patch("subprocess.run", return_value=mock_res):
        with pytest.raises(
            RuntimeError,
            match="agy returned SUCCESS with an empty response"
        ) as exc_info:
            executor.execute(plan, tmp_path)
        assert "agent hit max iterations" in str(exc_info.value)


def test_cli_success_whitespace_response(plan, tmp_path):
    # 3. SUCCESS + whitespace => failure
    executor = AntigravityCliExecutor()
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stderr = ""
    mock_res.stdout = json.dumps(
        {"status": "SUCCESS", "response": "   \n\t"}
    )

    with (
        patch("subprocess.run", return_value=mock_res),
        pytest.raises(RuntimeError, match="agy returned SUCCESS with an empty response")
    ):
        executor.execute(plan, tmp_path)


def test_cli_success_non_string_response(plan, tmp_path):
    # 4. SUCCESS + response non-string => failure
    executor = AntigravityCliExecutor()
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stderr = "some stderr"
    mock_res.stdout = json.dumps(
        {"status": "SUCCESS", "response": {"dict": "not string"}}
    )

    with patch("subprocess.run", return_value=mock_res):
        with pytest.raises(RuntimeError, match="is not a string") as exc_info:
            executor.execute(plan, tmp_path)
        assert "some stderr" in str(exc_info.value)


def test_returncode_not_zero(plan, tmp_path):
    # 8. returncode != 0 => error behavior preserved (and includes stderr)
    executor = AntigravityCliExecutor()
    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stderr = "error output"
    mock_res.stdout = ""
    with patch("subprocess.run", return_value=mock_res):
        with pytest.raises(RuntimeError, match="exit code 1") as exc_info:
            executor.execute(plan, tmp_path)
        assert "error output" in str(exc_info.value)


def test_empty_stdout(plan, tmp_path):
    # 9. stdout empty => error (and includes stderr)
    executor = AntigravityCliExecutor()
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stderr = "timeout"
    mock_res.stdout = "   "
    with patch("subprocess.run", return_value=mock_res):
        with pytest.raises(RuntimeError, match="agy returned empty stdout") as exc_info:
            executor.execute(plan, tmp_path)
        assert "timeout" in str(exc_info.value)


def test_invalid_json(plan, tmp_path):
    # 10. Invalid JSON => parse error (and includes stderr)
    executor = AntigravityCliExecutor()
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stderr = "segfault"
    mock_res.stdout = "not json"
    with patch("subprocess.run", return_value=mock_res):
        with pytest.raises(RuntimeError, match="Failed to parse") as exc_info:
            executor.execute(plan, tmp_path)
        assert "segfault" in str(exc_info.value)


def test_status_not_success(plan, tmp_path):
    # 11. status != SUCCESS => host execution error (and includes stderr)
    executor = AntigravityCliExecutor()
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stderr = "crash"
    mock_res.stdout = json.dumps({"status": "ERROR"})
    with patch("subprocess.run", return_value=mock_res):
        with pytest.raises(RuntimeError, match="non-SUCCESS status") as exc_info:
            executor.execute(plan, tmp_path)
        assert "crash" in str(exc_info.value)


def test_cli_timeout(plan, tmp_path):
    executor = AntigravityCliExecutor(timeout=1.0)
    with (
        patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="agy", timeout=1.0)),
        pytest.raises(RuntimeError, match="timed out")
    ):
        executor.execute(plan, tmp_path)


def test_cli_not_found(plan, tmp_path):
    executor = AntigravityCliExecutor()
    with (
        patch("subprocess.run", side_effect=FileNotFoundError),
        pytest.raises(RuntimeError, match="agy binary not found")
    ):
        executor.execute(plan, tmp_path)


def test_command_injection_prevention(plan, tmp_path):
    # Regression test
    plan_inj = AntigravityExecutionPlan(
        route_decision=plan.route_decision,
        orchestrator_handoff=plan.orchestrator_handoff,
        specialist_prompt="sys",
        workflow_prompt="wf",
        context_payload="ctx",
        restrictions=[],
        expected_output_contract=[],
        final_prompt='Do this"; rm -rf /; echo "done'
    )
    executor = AntigravityCliExecutor()
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stderr = ""
    mock_res.stdout = json.dumps({"status": "SUCCESS", "response": "done"})

    with patch("subprocess.run", return_value=mock_res) as mock_run:
        executor.execute(plan_inj, tmp_path)
        args = mock_run.call_args[0][0]
        assert 'Do this"; rm -rf /; echo "done' in args
