# Source of Truth Rules

## What Counts as Source of Truth

The only sources of truth in the AI Engineering Harness are:

1. **Files committed to the repository** — Code, schemas, policies, task contracts, evidence.
2. **Authority Matrix** (`core/authority/authority-matrix.yaml`) — Defines permissions.
3. **Task Contracts** (`projects/*/tasks/*.yaml`) — Define approved work.
4. **State Machine** (`core/schemas/state-machine.yaml`) — Defines valid transitions.
5. **Policies** (`core/policies/*.yaml`) — Define skip rules and exceptions.
6. **Evidence files** (`projects/*/evidence/*/EVIDENCE.md`) — Persistent quality records.

## What is NOT Source of Truth

1. **Chat conversation** — Conversation is ephemeral. It may inform decisions but is never authoritative.
2. **Agent memory or context** — Internal state is not verifiable.
3. **Verbal agreements** — Only written, committed artifacts count.
4. **Prior conversation history** — Decisions must be recorded in persistent files.

## Implications

- Never claim that a conversation message constitutes approval, acceptance, or authorization.
- Always write decisions, findings, and evidence to persistent files.
- When in doubt about the current state, read the actual files — do not rely on memory.
- If a discrepancy exists between conversation and files, files win.
