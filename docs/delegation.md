# Dynamic Specialist Delegation

The AI Engineering Harness utilizes a deterministic dynamic routing and delegation system to assign tasks to the correct specialist based on the intent, the active Task Contract, and the system's canonical sources.

## How It Works

1. **Deterministic Selection:** The system matches keywords from the task description or intent against the capabilities and purpose defined in `core/specialists/**/specialist.yaml`.
2. **Pre-approved Assignments:** If a Task Contract already has an approved specialist assigned, that assignment is never automatically overridden.
3. **Canonical Sources:** Only specialists that are explicitly authorized in `core/authority/authority-matrix.yaml` and exist in `core/specialists/` are eligible for assignment.
4. **Human Escalation:** In the event of a tie between multiple specialists, low confidence in a match, or a missing specialist, the system safely aborts automatic assignment and escalates to a human user (via `general-advisor`) for a decision.

## Supported Specialists

Delegation maps dynamically to various roles such as:
- `backend-engineer`
- `frontend-engineer`
- `database-engineer`
- `security-engineer`
- `documentation-engineer`
- `devops-release-engineer`
- and more, depending on the active catalog.
