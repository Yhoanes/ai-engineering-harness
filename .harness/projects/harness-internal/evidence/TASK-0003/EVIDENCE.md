# EVIDENCE: TASK-0003

## Acceptance Status
acceptance_status: passed
accepted_by: Yhoanes
accepted_at: 2026-08-28T18:46:09-04:00

## Final Status
status final: completed

## Validation Gates
- V4 PASS
- V2 in_progress -> completed PASS
- V5b final PASS

## Root Cause
V5b previously detected all untracked files identically, resulting in false positives for pre-existing untracked files that predated the task's implementation baseline.

## Implemented Design
The task schema `implementation_baseline` was extended to include an optional `preexisting_untracked` array. Each entry strictly maps a relative `path` to its `sha256`. The V5b validator (`validate_allowed_paths_post.py`) utilizes `hashlib.sha256` in binary chunk mode to securely snapshot untracked files without relying on unstable git timestamps. During detection, V5b skips untracked files that perfectly match both their initial path and SHA-256 hash. If they differ, or if the file was deleted, it flags them as tracked changes. 

## Behavior Matrix
| Scenario | Baseline Snapshot? | Result |
|----------|---------------------|--------|
| New untracked | Yes | **DETECTED** |
| Preexisting untracked (same hash) | Yes | **IGNORED** |
| Preexisting untracked (changed hash) | Yes | **DETECTED** |
| Preexisting untracked (deleted) | Yes | **DETECTED** |
| Staged / Unstaged / Committed | Yes | **DETECTED** |
| Legacy baseline, NO current untracked| No | **IGNORED (Compatible)** |
| Legacy baseline, HAS current untracked| No | **FAIL (CANNOT_VALIDATE)** |

## Tests
Added comprehensive test suite to `test_allowed_paths_post.py` spanning `AC-01` to `AC-20`, testing mocked hash and git operations. We also explicitly implemented the `HARNESS-0002.yaml` edge case demonstrating a safe-pass for the unchanged file, and a fail for a modified file.

## Pytest
100% PASS for all tests across the Harness (362 passed in 1.25s).

## Ruff
Code style validation and formatting completed. No blockers.

## Code Review
**Reviewer:** `code-reviewer`
**Status:** APPROVED
- Secure path helper explicitly validates against `repo_root`.
- Memory-safe hashing logic implemented (64KB chunks).
- Legacy fallback safely forces manual review rather than silently ignoring files.
- Verified set subtractions successfully merge Git and untracked file change deltas.

## Security Review
**Reviewer:** `security-engineer`
**Status:** PASSED
- `subprocess.run` executed securely without `shell=True`.
- Strict regex `^[a-f0-9]{64}$` enforcement against malformed/tampered baseline hashes.
- Fail-open vulnerabilities mitigated (legacy tasks fail securely).
- Path traversal completely neutralized by strict `resolve()` and `.relative_to()` constraints.
