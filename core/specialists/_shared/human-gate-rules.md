# Human Gate Rules

The following actions are **reserved exclusively for humans** and must never be performed by any specialist:

## Prohibited Actions

1. **Approving a Task Contract** — Only a human can set `approval_status: approved`.
2. **Accepting a task** — Only a human can set `acceptance_status: passed`.
3. **Closing a task** — Only a human can transition a task to `completed`.
4. **Overriding a validator failure** — If a gate fails, stop and report. Do not bypass.
5. **Granting permissions** — The Authority Matrix is human-maintained.

## When to Stop and Escalate to Human

- A validator gate fails.
- The requested work exceeds the Task Contract scope.
- You encounter ambiguity that could affect correctness or security.
- A design decision has not been explicitly made by the human.
- You need approval, acceptance, or closure of a task.
- The task requires modifying governance files (Authority Matrix, policies, schemas) without explicit authorization.

## How to Escalate

- State clearly what happened.
- Identify which gate or rule is involved.
- Propose options if applicable.
- Wait for human decision. Do not proceed.
