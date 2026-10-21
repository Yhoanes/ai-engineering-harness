# HARNESS-0016 Evidence

## Finding

`tests/test_export_builder.py::test_export_builder_dry` created a temporary repository
and ran `git commit` without an isolated identity. A fresh recovery PC correctly cloned
the private repository and installed the Harness, but the full suite reported exit 128
because no global Git author identity existed.

## Root Cause

The test fixture depended implicitly on external user configuration. The product export
builder was not reached by the failing execution.

## Correction

The temporary commit now uses command-scoped configuration:

- `-c user.name=AI Engineering Harness Tests`
- `-c user.email=harness-tests@example.invalid`

The values apply only to that Git invocation. No global or repository identity is stored.

## Documentation

- `README.md` includes the complete Windows test commands.
- `docs/installation.md` identifies Git as required for history export and full tests.
- Both explicitly state that global Git identity is not required.

## Recovery Evidence

- Private clone: PASS
- Commit count: 49
- Tags recovered: `v1.0.0`, `v1.1.0`
- Head recovered: `814fd0895224de615dd656876de1ccedbc034ce8`
- Portable installer on Python 3.14.5: `STATUS: READY`
- Pre-fix clean-machine suite: 453 passed, 3 skipped, 1 failed
- Temporary environment confirmation: 454 passed, 3 skipped
- Corrected primary suite with global identity hidden: 455 passed, 2 skipped

Skip counts differ by supported Python/environment conditions and are not failures.

## Reviews

- Ruff: PASS
- Version consistency: PASS
- Diff whitespace check: PASS
- Code review: APPROVED
- Security review: PASS

## Deviation

The user authorized correction immediately after the recovery defect was reproduced.
The three initial corrective changes preceded task-contract materialization. Their scope
was preserved, reviewed, and fully validated before v1.1.1 release packaging. The
certified v1.1.0 commit and tag were not modified.
