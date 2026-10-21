# Proposal: HARNESS-0020 — Governed Autonomous Workflow Execution

## 1. Problem Statement
Currently, the Harness requires the user to manually copy instructions (prompts) between the Advisor, Orchestrator, and Specialists. The `AntigravityAdapter.execute()` exists but relies on an external `AntigravityExecutor` and only executes a single step. The system lacks the capability to autonomously progress through the lifecycle of a task (plan -> approve -> implement -> review -> accept -> close) while still respecting mandatory human gates.

## 2. Objective
Create a Governed Autonomous Workflow Execution layer that can automatically string together handoffs between the Router, Orchestrator, and appropriate Specialists. The execution must pause at defined "human gates" (e.g., awaiting task approval, or final task acceptance) and must dynamically route the execution based on the current state.

## 3. Architecture Proposed
The architecture will clearly separate the following concerns:

### 3.1 Planning / Routing
- Leverages the existing `Router` and `Orchestrator` to determine the next workflow step and the appropriate specialist (dynamic delegation using v1.3.0 logic).
- Generates the `AntigravityExecutionPlan` containing prompt bundles and restrictions.

### 3.2 Execution
- A new `AutonomousRunner` component that acts as the loop controller.
- **Harness Autonomy vs. Host Execution:** The Harness dictates the logical flow, states, and prompts (Autonomy). The physical execution of AI requests and tool calls is provided by the Antigravity host platform via the `AntigravityExecutor` interface. The Harness does not assume native Antigravity subagent APIs; instead, it sequences states and utilizes the existing adapter contract to invoke the LLM context.
- Implements a configurable `max_steps` limit to explicitly prevent infinite loops.

### 3.3 Human Gates
- Hard stops engineered into the execution loop.
- **Gate 1 (Task Approval):** Pauses when a task enters `awaiting_approval`. Resumes only upon explicit human approval.
- **Gate 2 (Task Acceptance):** Pauses when a task is `completed` (or with deviation) and `acceptance_status` is pending.
- **Gate 3 (Escalation/Safety):** Pauses if there is a scope change, an unhandled error, a tie in routing, low confidence, lack of authority, missing specialist, or if max steps are reached.

### 3.4 Session Persistence & Resumption
- The `task_contract.yaml` remains the single source of truth for the task's state.
- **Resuming after a human gate:** The human approval must be recorded. The Runner then reloads the Task Contract from disk, reevaluates the next step via the Router and State Machine, and dynamically generates a new plan. It must **never blindly reuse an older plan** if the contract or state changed.

### 3.5 Audit Trail
- Full traceability of every handoff and transition.
- **Step Distinction:** Each step will be clearly categorized as `planned`, `dispatched`, `executed`, `paused`, `failed`, or `completed` so the audit trail accurately reflects physical execution vs. intent.
- The Harness must never claim it executed a specialist if the host/executor did not actually dispatch the invocation.

### 3.6 Antigravity Specific Integration
- Extends or wraps `AntigravityAdapter.execute()` to loop while conditions permit.
- Ensures compatibility with existing slash commands (`/advisor`, `/new-project`, `/evolve-harness`) by mapping them to appropriate entry points in the autonomous loop.

## 4. Affected Files
- `adapters/antigravity/adapter.py` (Enhance loop logic)
- `adapters/antigravity/models.py` (Add configuration for `max_steps`, loop state, audit trail)
- `adapters/antigravity/autonomous_runner.py` (New file for the autonomous loop executor)
- `engine/router/router.py` & `engine/router/models.py` (Proper mapping when resuming)
- `engine/state_machine/transitions.py` (Helper functions for human gate detection)
- `engine/orchestrator/orchestrator.py` (Handoff adjustments for continuous execution)

## 5. Acceptance Criteria
See `HARNESS-0020.yaml` for the definitive acceptance criteria.
