# HARNESS-0021 Evidence

## Baseline
- v1.4.0 (AutonomousRunner without physical bridge)
- Architecture defined in HARNESS-0021.md and HARNESS-0021.yaml

## Architecture Implemented

### AntigravityCliExecutor
Official bridge executing `agy` in subprocess, processing `--output-format json`
safely with timeouts and robust parsing.

### StagingSandbox
Temporary zone for `plan-task` where the Task Contract draft is generated.
If the Harness validates the YAML, it is copied to the official repo.

### WorktreeSandbox + SandboxChange
Git worktree isolating `implement-task` mutations. After execution, the Harness
inspects the diff at filesystem level using `git status --porcelain -uall`.
Each change is classified as `SandboxChange(status, path, old_path)` where
status is A (create), M (modify), D (delete), or R (rename).
`apply_to_main()` enforces operation-specific semantics per status.

### Scope Enforcement
Cross-validation against `scope.planned_paths.modify`. For renames, both
`old_path` and `path` must be in scope. Out-of-scope files → `RuntimeError`,
no `validated`, no `applied`.

### Workflow Mode Classification
Autonomous execution is restricted to authorized workflow modes:
- **PLANNING_WORKFLOWS** (`plan-task`): uses `StagingSandbox`
- **MUTATIONAL_WORKFLOWS** (`implement-task`): uses `WorktreeSandbox`
- **All other workflows** (`discuss`, `approve-task`, `review-task`, etc.):
  paused immediately with reason "not enabled for autonomous physical execution"

### Governed Exit After Implementation
After `implement-task → applied`, the Runner emits `paused` with reason
`"Implementation applied. Awaiting governed review."` and stops.
No second iteration. No `discuss` fallback. No `max_steps` as normal exit.

---

## E2E Phase 1 — Planning Real

- **Test**: `tests/test_e2e_runner.py`
- **Command**: `$env:HARNESS_RUN_ANTIGRAVITY_E2E="1"; pytest tests/test_e2e_runner.py -s -v`
- **Executor**: AntigravityCliExecutor (agy real with `--dangerously-skip-permissions`)
- **Project**: `.harness-internal` (canonical key with leading dot)
- **Audit trail**:
  - Step 1: `planned → sandbox_created → dispatched → executed → validated → applied` (plan-task)
  - Step 2: `planned → paused` (approve-task, Human Gate: awaiting_approval)
- **Task Contract**: TASK-9999.yaml generated physically in StagingSandbox
- **task_id propagation**: Extracted from generated contract, propagated to `current_request`
- **Gate**: Paused by `Human Gate: Task is awaiting_approval` (not `max_steps`)
- **Cleanup**: TASK-9999.yaml and evidence/TASK-9999/ removed after test

---

## E2E Phase 2 — Implementation Real

- **Test**: `tests/test_e2e_implement.py`
- **Command**: `$env:HARNESS_RUN_ANTIGRAVITY_E2E="1"; pytest tests/test_e2e_implement.py -s -v`
- **Execution date**: 2026-08-30T23:33:26Z
- **HEAD baseline**: `9b58f6a776db6f01657c54de0658577ec8719156`
- **Branch**: `master`
- **Executor**: AntigravityCliExecutor (agy real)
- **agy conversation**: `9b1ade9f-d513-4c08-b8ca-ab2c70824b00` (44.97s, 1 turn)
- **Worktree**: `C:/Users/Usuario/AppData/Local/Temp/harness-worktree-*` (temporary, cleaned)

### Audit Trail (exact)
```
Step 1: planned      workflow='implement-task'  specialist='frontend-engineer'
Step 1: sandbox_created
Step 1: dispatched   host_executor='agy_cli'
Step 1: executed     host_executor='agy_cli'
Step 1: validated
Step 1: applied
Step 1: paused       reason='Implementation applied. Awaiting governed review.'
```

### Verified Properties
- ✅ `e2e_contador.html` created physically inside worktree by agy real
- ✅ Content: `hello`
- ✅ `get_diff()` detected `SandboxChange(status='A', path='projects/.harness-internal/scratch/e2e_contador.html')`
- ✅ Scope validation passed (file in `planned_paths.modify`)
- ✅ `validated` emitted
- ✅ `apply_to_main()` transferred file to main repo
- ✅ `applied` emitted
- ✅ `paused` with reason `"Implementation applied. Awaiting governed review."`
- ✅ One single agy execution (1 turn)
- ✅ No Step 2 with `workflow='discuss'`
- ✅ Not terminated by `max_steps`
- ✅ HEAD unchanged after test: `9b58f6a`
- ✅ Branch unchanged: `master`
- ✅ Tags unchanged: `v1.0.0` through `v1.4.0`
- ✅ Worktree cleaned up (only main worktree remains)
- ✅ Cleanup removed `TASK-9998.yaml`, `evidence/TASK-9998/`, `e2e_contador.html`

### Note on pytest Exit Code
The full `pytest tests/test_e2e_implement.py` exited FAILED because the
original test file contained a second section that attempted to force agy to
create `OUT_OF_SCOPE.txt` outside the approved scope. agy self-policed and
refused, producing an empty diff instead of a scope violation. The assertion
`"Scope violation" in stdout` failed. The test file has since been refactored
to validate only the implementation path. Scope enforcement is tested
deterministically in `test_worktree_scope_integration.py`.

---

## Harness Scope Enforcement (Layer B)

- **Test**: `tests/test_worktree_scope_integration.py`
- **Method**: Deterministic — does NOT depend on LLM behavior
- **Infrastructure**: Real git repo, real `WorktreeSandbox`, real `get_diff()`, real `apply_to_main()`

### test_rogue_file_detected_by_scope_validation ✅
- Executor writes both `allowed.html` and `OUT_OF_SCOPE.txt` into worktree
- Real `get_diff()` detects both files with `status='A'`
- Scope validation identifies `OUT_OF_SCOPE.txt` as out-of-scope
- Only `allowed.html` is applied to main
- `OUT_OF_SCOPE.txt` never reaches main

### test_rogue_file_full_rejection ✅
- Both allowed and rogue files written to worktree
- Out-of-scope detected → entire apply skipped
- Neither file reaches main

### test_delete_requires_git_status_d ✅
- File absent in sandbox without `D` status → NOT deleted from main
- Protects against false inference of deletion

---

## Bugs Discovered and Fixed

### BUG 1: No Exit After Applied
After `implement-task → applied`, the Runner continued iterating, falling to
`discuss` workflow on Step 2. Fixed by adding governed exit after applied.

### BUG 2: discuss Treated as Mutational
Router default (`discuss`) received `WorktreeSandbox` and produced `validated`
and `applied` with empty changes. Fixed by classifying workflow modes.

### BUG 3: No Workflow Mode Classification
All non-`plan-task` workflows received `WorktreeSandbox`. Fixed by restricting
`WorktreeSandbox` to `MUTATIONAL_WORKFLOWS` only.

---

## Deviations

### Deviation 1: AutonomousRunner modifications
- **Files**: `adapters/antigravity/autonomous_runner.py`
- **Reason**: Centralized sandbox lifecycle in Runner instead of Orchestrator
- **Documented**: Yes
- **authorized_by**: Yhoanes
- **accepted_by**: Yhoanes
- **accepted_at**: 2026-08-30T19:44:45-04:00

### Deviation 2: Canonical project key support
- **Files**: `adapters/antigravity/adapter.py`, `engine/context/loader.py`,
  `tests/test_antigravity_adapter.py`, `tests/test_context_loader.py`
- **Reason**: Support `.harness-internal` canonical project key with path traversal protection
- **Documented**: Yes
- **authorized_by**: Yhoanes
- **accepted_by**: Yhoanes
- **accepted_at**: 2026-08-30T19:44:45-04:00

> Acceptance of these deviations applies only to HARNESS-0021. It does not
> constitute retroactive authorization of the original scope nor automatic
> precedent for future tasks.

---

## Human Acceptance

- **Accepted by**: Yhoanes
- **Accepted at**: 2026-08-30T19:44:45-04:00
- **status**: `completed_with_deviation`
- **acceptance_status**: `passed_with_deviation`
- **Both deviations accepted**: Yes

### Summary of Completed Evidence
- ✅ **Phase 1** — Planning real with agy, staging, Task Contract, Human Gate
- ✅ **Phase 2** — Implementation real with worktree, agy, physical file, validated, applied, governed pause
- ✅ **Harness Scope Enforcement** — Deterministic rogue file rejection with real worktree
- ✅ **Bugs Fixed** — No post-applied discuss, workflow mode classification, governed exit
- ✅ **Pytest**: 515 passed, 4 skipped, 0 errors
- ✅ **Ruff**: All checks passed
- ✅ **git diff --check**: Clean
- ✅ **Diagnostics**: STATUS: READY (10/10 PASS)
- ✅ **Validator**: HARNESS-0021.yaml valid (exit 0)
