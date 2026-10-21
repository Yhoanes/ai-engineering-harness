# HARNESS-0019 Acceptance Evidence

**Status:** PASSED
**Validator:** Yhoanes
**Date:** 2026-08-30T13:58:39-04:00

## Release v1.3.0

This scope was extended to include the `v1.3.0` bump in `VERSION` and `pyproject.toml`, as well as creating `docs/releases/v1.3.0.md`.

## Validation Summary

- **Tests:** 477 passed, 2 skipped
- **Ruff:** PASSED (`All checks passed!`)
- **Git Check:** `git diff --check` PASSED (no trailing whitespaces or EOF blank line errors)
- **Diagnostics:** `STATUS: READY` (all subsystems verified)
- **Hardcodes Check:** `grep "backend-engineer" engine/router/specialist_selector.py` verified to yield zero hardcoded results.

## Acceptance Criteria Verified

### 1. Dynamic Discovery (No Hardcoded Names)
The dictionary of hardcoded keywords in `engine/router/specialist_selector.py` was completely removed. Selection dynamically parses all profiles in `core/specialists/` (extracting `id`, `display_name`, `description`, `purpose`, and `capabilities`). The test `test_dynamic_discovery.py` verifies this by injecting an `alien-engineer` into a temporary structure and confirming it gets selected correctly without Python modifications.

### 2. Authority Check
Selection now filters matching profiles against the `workflow.yaml` allowed specialists. A negative test (`test_dynamic_selection_unauthorized_specialist_escalates`) confirms that if a profile (like `code-reviewer`) matches keywords but lacks authority for an implementation workflow, it correctly escalates to human instead of assigning illegally.

### 3. Human Escalation (Tie/Low Confidence)
Escalation remains deterministically guaranteed. When multiple identical scores are found (e.g. `test_dynamic_selection_tie_escalates`), or when confidence is too low, the router falls back to `discuss` / `general-advisor`.

### 4. Preservation of Pre-Approved Assignments
`test_dynamic_selection_preserves_pre_approved` explicitly guarantees that tasks already containing valid `assigned_specialists` skip selection and keep their approved assignments.

### 5. Task Validation Rule
An explicit rule was added to `engine/validators/validate_task_contract.py` ensuring that `approved` or active contracts can never have an empty `assigned_specialists` array, forcing early termination of invalid state.
