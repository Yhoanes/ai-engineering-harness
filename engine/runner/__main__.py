import argparse
from pathlib import Path

from adapters.antigravity.adapter import AntigravityAdapter
from adapters.antigravity.autonomous_runner import AutonomousRunner
from adapters.antigravity.cli_executor import AntigravityCliExecutor
from adapters.antigravity.models import AntigravityRequest
from engine.execution.models import ExecutionStatus


def _exit_code_for_execution_status(status: ExecutionStatus) -> int:
    mapping = {
        ExecutionStatus.COMPLETED: 0,
        ExecutionStatus.FAILED: 11,
        ExecutionStatus.BLOCKED: 12,
        ExecutionStatus.INCOMPLETE: 13,
        ExecutionStatus.CANCELLED: 14,
    }
    return mapping.get(status, 20)


def _exit_code_for_legacy_trail(trail: list) -> int:
    if not trail:
        return 13

    mapping = {
        "completed": 0,
        "failed": 11,
        "paused": 12,
        "incomplete": 13,
    }
    return mapping.get(trail[-1].status, 20)


def main() -> int:
    parser = argparse.ArgumentParser(description="Antigravity Harness Entrypoint")
    parser.add_argument("--project", required=True, help="Project name (e.g., _harness-internal)")
    parser.add_argument("--intent", required=True, help="Initial user intent")
    parser.add_argument("--task-id", help="Existing task ID to resume")
    parser.add_argument("--max-steps", type=int, default=5, help="Max autonomous steps")
    parser.add_argument(
        "--dangerously-skip-permissions",
        action="store_true",
        help="Privileged mode: allow tools to run in sandbox without prompting",
    )

    parser.add_argument(
        "--execution-mode",
        choices=["legacy", "provider"],
        default="legacy",
        help="Execution mode (legacy or provider)"
    )

    args = parser.parse_args()

    repo_root = Path.cwd()

    if args.execution_mode == "provider":
        from adapters.antigravity.execution_provider import AntigravityExecutionProvider
        from engine.orchestrator.engine import HarnessEngine

        provider = AntigravityExecutionProvider()
        engine = HarnessEngine(repo_root=repo_root, provider=provider)

        print(f"Starting provider mode for project {args.project}...")
        result = engine.run_task(args.project, args.task_id, args.intent)
        print(f"Execution complete. Status: {result.status.name}")
        return _exit_code_for_execution_status(result.status)

    adapter = AntigravityAdapter(repo_root=repo_root)

    executor = AntigravityCliExecutor(
        dangerously_skip_permissions=args.dangerously_skip_permissions
    )

    runner = AutonomousRunner(adapter=adapter, executor=executor)

    request = AntigravityRequest(
        project=args.project,
        user_input=args.intent,
        task_id=args.task_id,
    )

    print(f"Starting autonomous runner for project {args.project}...")
    trail = runner.run(request, max_steps=args.max_steps)

    print("\nExecution complete. Final audit trail:")
    for entry in trail:
        print(entry)

    return _exit_code_for_legacy_trail(trail)


if __name__ == "__main__":
    import sys
    sys.exit(main())
