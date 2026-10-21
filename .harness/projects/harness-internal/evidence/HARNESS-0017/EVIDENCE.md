# HARNESS-0017 Evidence

## Outcome

The root-level `INSTALAR.cmd` launcher and release `v1.1.2` passed the approved
acceptance criteria. No user project content was modified.

## Installation validation

- Command: `install/setup.ps1 -Mode Development -Repair`
- Installed package version: `1.1.2`
- Diagnostics: all required components `PASS`
- Final status: `STATUS: READY`

## Automated tests

- Command: `.venv/Scripts/python.exe -m pytest -p no:cacheprovider`
- Result: `458 passed, 2 skipped`
- Total collected: `460`
- Duration: `3.79s`
- Installer launcher acceptance tests: `3 passed`
- Version consistency: passed
- Distribution inclusion and validation: passed

The first publication-runner attempt invoked pytest with the correct test path but
from the runner's output directory. Two legacy workflow tests derive their repository
root from the current working directory and therefore failed to locate `core/`.
Re-running from `C:\ai-engineering-harness` produced the clean result above. This was
a runner-location issue, not a Harness product failure.

## Quality and security review

- Ruff: `All checks passed!`
- Git whitespace/integrity check: passed
- Launcher resolves `install/setup.ps1` through `%~dp0`; no machine path is embedded.
- Paths containing spaces are quoted.
- PowerShell execution-policy bypass is process-scoped.
- The launcher does not download Python, install global dependencies, or modify projects.
- The underlying bootstrap exit code is preserved and the final result remains visible.

## Scope review

Only the thirteen paths recorded in the task postcheck were changed. Existing
`projects/` content, the `v1.1.1` commit, and the `v1.1.1` tag remain unchanged.

## Acceptance

Accepted by Yhoanes on 2026-08-30 after successful clean validation.
