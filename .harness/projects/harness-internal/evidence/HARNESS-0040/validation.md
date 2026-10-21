# Validation of HARNESS-0040

- **original installer issue**: Installer missed adapters/core in packaging and caught Write-Error unexpectedly during python version checks.
- **Python comparison fix**: Now uses .Split('.') and numerical comparison, emitting a warning and cleanly exiting 2.
- **requires-python >=3.11**: pyproject.toml preserves requires-python = ">=3.11".
- **setup hardcodes minimum 3.11**: setup.ps1 has an explicit duplication of 3.11 logic (-lt 3 -or ( -eq 3 -and  -lt 11)).
- **drift risk documented**: Yes. setup.ps1 currently duplicates the pyproject.toml contract rather than extracting it dynamically. For v1.13.5 this is acceptable, but any future requirements changes must update both files simultaneously.
- **previous setuptools include**: ["engine*"]
- **new setuptools include**: ["engine*", "adapters*", "core*"]
- **engine/adapters/core classification**: Classified as Python runtime packages (core containing namespace sub-packages).
- **exact package-data patterns**: "*" = ["*.yaml", "*.md"]
- **MODEL B portable root + venv**: Explicitly acknowledged. Portable root resources (.agents/, skills/, templates/, workflows/) remain in portable root. Python modules go to site-packages.
- **fresh-CWD installed paths**:
    engine: C:\temp\test_dist\venv\Lib\site-packages\engine\__init__.py
    adapters.antigravity: C:\temp\test_dist\venv\Lib\site-packages\adapters\antigravity\__init__.py
    core: C:\temp\test_dist\venv\Lib\site-packages\core
- **schemas installed**: C:\temp\test_dist\venv\Lib\site-packages\core\schemas
- **authority YAML installed**: C:\temp\test_dist\venv\Lib\site-packages\core\authority
- **source-tree Python dependency eliminated**: Yes.
- **portable-root dependency intentional**: Yes.
- **Python 3.10 simulated result**: Exits 2. Stdout/Stderr contained "PYTHON_VERSION_UNSUPPORTED".
- **Python 3.12 simulated result**: Passed the python version block without error.
- **supported test does NOT assert complete setup exit 0**: The test environment only verifies the script bypasses the version check; it verifies "PYTHON_VERSION_UNSUPPORTED" is not emitted, but does not rely on a complete exit 0.
- **exact -Check semantics**: Resolves paths -> verifies Python version bounds -> checks if .venv exists. If not, returns 2 (STATUS: NOT_INSTALLED). If exists, executes engine.diagnostics and exits its %LASTEXITCODE%.
- **installer tests**: 5 passed.
- **distribution tests**: 6 passed, 1 skipped.
- **full suite**: 681 passed, 4 skipped. (baseline + 2 added = 685 collected).
- **Ruff deviation**: During implementation, uff --fix was accidentally executed on 	ests/test_installer_launcher.py. It strictly fixed whitespace formatting and removed an unused import sys on the test file. No out-of-scope files were touched.
- **final Ruff no-fix PASS**: PASS.
- **diagnostics READY**: PASS.
- **Task CLI validation PASS**: PASS.
- **authoritative loader PASS**: PASS.
- **Matrix validation PASS**: PASS.
- **HARNESS-0022 untouched**: Yes.
- **Human Acceptance by Yhoanes**: Approved and completed.
