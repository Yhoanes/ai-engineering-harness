# Task Contract Rules

Every specialist must respect the Task Contract as the governing agreement for any work.

## Before Starting Work

- Verify the Task Contract exists and is approved (`approval_status: approved`).
- Verify you are listed in `assigned_specialists` (for implementation) or authorized via `task_management.review` (for reviews).
- Verify the task status allows the action you intend to perform.
- Read `scope.planned_paths.modify` to understand what files you may change.
- Read `scope.planned_paths.read` to understand what context is available.

## During Work

- Only modify files listed in `scope.planned_paths.modify`.
- Only use terminal commands listed in `scope.allowed_actions.terminal`.
- Do not perform actions listed in `scope.forbidden_actions`.
- If you discover work that exceeds the contract scope, stop and escalate.
- Do not silently expand the scope of a task.

## Evidence

- Record all evidence in the `evidence` section of the Task Contract.
- Generate persistent evidence files at the path specified by the contract.
- Tests must be run and results recorded before requesting acceptance.
- Code review and security review must be completed by independent reviewers.

## Completion

- Do not change `acceptance_status`, `accepted_by`, or `accepted_at`.
- Do not transition `status` to `completed` — this is a human action.
- When implementation is done, report results and wait for human acceptance.
