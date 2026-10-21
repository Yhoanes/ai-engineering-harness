# Proposal: HARNESS-0019 - Dynamic Specialist Selection & Delegation

## 1. Overview
The current Harness architecture has hardcoded specialist assignments, specifically defaulting to `backend-engineer`. This proposal introduces a dynamic, deterministic routing and delegation mechanism to correctly assign tasks to the appropriate specialists based on their capabilities, the workflow context, and the active Task Contract.

## 2. Problem Statement
The following issues have been confirmed and need to be resolved:
*   The Router currently assigns `backend-engineer` automatically for approved implementations, ignoring other potential specialists.
*   The Orchestrator generates Task Contracts with a hardcoded `assigned_specialists: ["backend-engineer"]` list.

## 3. Objectives
To build a scalable and flexible agent routing system, this proposal aims to implement the following:
*   **Deterministic Selection:** Base specialist selection on a matching algorithm evaluating the task context against canonical sources: `core/specialists/**`, `core/workflows/**`, and `core/authority/authority-matrix.yaml`. The selection must be perfectly reproducible (same inputs and catalog yield same outputs).
*   **Eliminate Hardcoding:** Remove all instances of hardcoded specialists (e.g., `backend-engineer`) from the Router and Orchestrator. No specialist names will be created that do not exist in the canonical catalog.
*   **Preserve Approvals:** Ensure that any specialist assignments that have already been explicitly approved in a Task Contract are never automatically replaced or overwritten.
*   **Human Escalation:** Safely escalate to human approval in edge cases such as ties between specialists, low-confidence matches, or non-existent specialists. No arbitrary choices will be made.
*   **Robust Validation:** Validate that all selectable specialists genuinely exist in `core/specialists/` and are explicitly authorized for the corresponding workflow.
*   **Compatibility:** Maintain full compatibility with `/new-project` and Antigravity native integration. `/new-project` must continue to be conversational and read-only until human approval is obtained.
*   **System Integrity:** Update all relevant test suites to cover at least backend, frontend, database, security, documentation, and release scenarios, alongside diagnostics and documentation updates.

## 4. Proposed Implementation Steps
1.  **Catalog & Heuristics Update:** Create a dedicated selection module (e.g., `engine/router/specialist_selector.py`) to parse canonical catalogs and perform deterministic specialist matching.
2.  **Router Modification:** Update `engine/router/router.py` (and `engine/router/models.py` if needed) to invoke the dynamic selection mechanism instead of defaulting to `backend-engineer`.
3.  **Orchestrator Modification:** Update `engine/orchestrator/orchestrator.py` (and `engine/orchestrator/models.py` if needed) to generate dynamic contracts while preserving explicitly pre-approved specialist assignments.
4.  **Escalation Logic:** Add fallback behavior to prompt the user or fail safely with a descriptive error requiring human intervention when a clear specialist cannot be determined or validated.
5.  **Validation:** Run the diagnostic engine and the test suite to ensure the changes do not break Antigravity integration or `/new-project` flows, verifying the scenarios outlined in the acceptance criteria.

## 5. Status
*   **Proposal Status:** `awaiting_approval`
*   **Approval Status:** `pending`
