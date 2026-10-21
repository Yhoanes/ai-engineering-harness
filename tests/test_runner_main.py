import runpy
from unittest.mock import MagicMock, patch

import pytest

from adapters.antigravity.models import AuditTrailEntry
from engine.execution.models import ExecutionStatus
from engine.runner.__main__ import _exit_code_for_execution_status, main


def test_provider_completed_returns_0():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "provider"]
    with patch("sys.argv", argv), patch("engine.orchestrator.engine.HarnessEngine.run_task") as m:
        mock_result = MagicMock()
        mock_result.status = ExecutionStatus.COMPLETED
        m.return_value = mock_result
        assert main() == 0


def test_provider_failed_returns_11():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "provider"]
    with patch("sys.argv", argv), patch("engine.orchestrator.engine.HarnessEngine.run_task") as m:
        mock_result = MagicMock()
        mock_result.status = ExecutionStatus.FAILED
        m.return_value = mock_result
        assert main() == 11


def test_provider_blocked_returns_12():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "provider"]
    with patch("sys.argv", argv), patch("engine.orchestrator.engine.HarnessEngine.run_task") as m:
        mock_result = MagicMock()
        mock_result.status = ExecutionStatus.BLOCKED
        m.return_value = mock_result
        assert main() == 12


def test_provider_incomplete_returns_13():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "provider"]
    with patch("sys.argv", argv), patch("engine.orchestrator.engine.HarnessEngine.run_task") as m:
        mock_result = MagicMock()
        mock_result.status = ExecutionStatus.INCOMPLETE
        m.return_value = mock_result
        assert main() == 13


def test_provider_cancelled_returns_14():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "provider"]
    with patch("sys.argv", argv), patch("engine.orchestrator.engine.HarnessEngine.run_task") as m:
        mock_result = MagicMock()
        mock_result.status = ExecutionStatus.CANCELLED
        m.return_value = mock_result
        assert main() == 14


def test_provider_unknown_returns_20():
    assert _exit_code_for_execution_status("UNKNOWN_MOCK_VALUE") == 20


def test_provider_exception_propagates():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "provider"]
    with patch("sys.argv", argv), patch("engine.orchestrator.engine.HarnessEngine.run_task") as m:
        m.side_effect = RuntimeError("Something went wrong internally")
        with pytest.raises(RuntimeError):
            main()


def test_legacy_completed_returns_0():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "legacy"]
    p_path = "adapters.antigravity.autonomous_runner.AutonomousRunner.run"
    with patch("sys.argv", argv), patch(p_path) as m:
        m.return_value = [AuditTrailEntry(step=1, status="completed")]
        assert main() == 0


def test_legacy_failed_returns_11():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "legacy"]
    p_path = "adapters.antigravity.autonomous_runner.AutonomousRunner.run"
    with patch("sys.argv", argv), patch(p_path) as m:
        m.return_value = [AuditTrailEntry(step=1, status="failed")]
        assert main() == 11


def test_legacy_paused_returns_12():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "legacy"]
    p_path = "adapters.antigravity.autonomous_runner.AutonomousRunner.run"
    with patch("sys.argv", argv), patch(p_path) as m:
        m.return_value = [AuditTrailEntry(step=1, status="paused")]
        assert main() == 12


def test_legacy_incomplete_returns_13():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "legacy"]
    p_path = "adapters.antigravity.autonomous_runner.AutonomousRunner.run"
    with patch("sys.argv", argv), patch(p_path) as m:
        m.return_value = [AuditTrailEntry(step=1, status="incomplete")]
        assert main() == 13


def test_legacy_empty_trail_returns_13():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "legacy"]
    p_path = "adapters.antigravity.autonomous_runner.AutonomousRunner.run"
    with patch("sys.argv", argv), patch(p_path) as m:
        m.return_value = []
        assert main() == 13


def test_legacy_unknown_status_returns_20():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "legacy"]
    p_path = "adapters.antigravity.autonomous_runner.AutonomousRunner.run"
    with patch("sys.argv", argv), patch(p_path) as m:
        m.return_value = [AuditTrailEntry(step=1, status="unknown_mock_status")]
        assert main() == 20


def test_executable_boundary_system_exit():
    argv = ["__main__.py", "--project", "test", "--intent", "test", "--execution-mode", "provider"]
    with patch("sys.argv", argv), patch("engine.orchestrator.engine.HarnessEngine.run_task") as m:
        mock_result = MagicMock()
        mock_result.status = ExecutionStatus.BLOCKED
        m.return_value = mock_result
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("engine.runner.__main__", run_name="__main__")
        assert exc_info.value.code == 12
