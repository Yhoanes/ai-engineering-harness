import json
import subprocess
from pathlib import Path

from adapters.antigravity.models import (
    AntigravityExecutionPlan,
    AntigravityExecutor,
    AntigravityResponse,
)


def _truncate_diagnostic(text: str | None, max_chars: int = 8192) -> str:
    if text is None:
        return ""
    if len(text) > max_chars:
        return text[:max_chars] + "... (truncated)"
    return text


class AntigravityCliExecutor(AntigravityExecutor):
    def __init__(self, timeout: float = 630.0, dangerously_skip_permissions: bool = False):
        self.timeout = timeout
        self.dangerously_skip_permissions = dangerously_skip_permissions

    def execute(self, plan: AntigravityExecutionPlan, sandbox_dir: Path) -> AntigravityResponse:
        cmd = [
            "agy",
            "--print",
            plan.final_prompt,
            "--output-format",
            "json",
            "--print-timeout",
            "10m",
            "--add-dir",
            str(sandbox_dir.absolute()),
        ]

        if plan.orchestrator_handoff.project:
            cmd.extend(["--project", plan.orchestrator_handoff.project])

        # Pass --agent so agy knows which specialist to use
        if plan.route_decision.primary_specialist:
            cmd.extend(["--agent", plan.route_decision.primary_specialist])

        if self.dangerously_skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        try:
            res = subprocess.run(
                cmd,
                shell=False,
                cwd=str(sandbox_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"agy process timed out after {self.timeout}s: {str(e)}") from e
        except FileNotFoundError as e:
            raise RuntimeError("agy binary not found. Ensure it is installed and in PATH.") from e

        bounded_stderr = _truncate_diagnostic(res.stderr)

        if res.returncode != 0:
            msg = (
                f"agy process failed with exit code {res.returncode}. "
                f"stderr: {bounded_stderr} stdout: {res.stdout}"
            )
            raise RuntimeError(msg)

        if not res.stdout.strip():
            raise RuntimeError(f"agy returned empty stdout. stderr: {bounded_stderr}")

        try:
            parsed = json.loads(res.stdout)
            print(f"DEBUG E2E AGY PARSED: {parsed}")
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse agy JSON output: {e}\n"
                f"Output: {res.stdout}\nstderr: {bounded_stderr}"
            ) from e

        if parsed.get("status") != "SUCCESS":
            msg = (
                f"agy returned non-SUCCESS status: {parsed.get('status')}. "
                f"Output: {res.stdout} stderr: {bounded_stderr}"
            )
            raise RuntimeError(msg)

        if "response" not in parsed:
            raise RuntimeError(
                f"agy JSON output missing 'response' field. stderr: {bounded_stderr}"
            )

        response_val = parsed["response"]
        if not isinstance(response_val, str):
            raise RuntimeError(
                f"agy JSON output 'response' is not a string. stderr: {bounded_stderr}"
            )

        if not response_val.strip():
            msg = (
                f"agy returned SUCCESS with an empty response. "
                f"num_turns={parsed.get('num_turns')}, duration={parsed.get('duration_seconds')}s. "
                f"stderr: {bounded_stderr}"
            )
            raise RuntimeError(msg)

        metadata = {
            "conversation_id": parsed.get("conversation_id"),
            "status": parsed.get("status"),
            "num_turns": parsed.get("num_turns"),
            "duration_seconds": parsed.get("duration_seconds"),
            "usage": parsed.get("usage", {}),
            "stderr": bounded_stderr,
            "returncode": res.returncode,
            "host_executor": "agy_cli",
        }

        return AntigravityResponse(
            raw_text=response_val,
            metadata=metadata,
        )
