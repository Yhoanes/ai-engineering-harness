from pathlib import Path

from engine.diagnostics.engine import (
    _check_python_version,
    _get_python_requirement,
    run_diagnostics,
)


def test_python_requirement_reading(tmp_path: Path):
    pyproj = tmp_path / "pyproject.toml"
    pyproj.write_text('requires-python = ">=3.11"', encoding="utf-8")
    assert _get_python_requirement(tmp_path) == ">=3.11"

    pyproj.write_text('requires-python = ">=3.12"', encoding="utf-8")
    assert _get_python_requirement(tmp_path) == ">=3.12"


def test_check_python_version():
    check_pass = _check_python_version(">=3.8")
    assert check_pass.status == "PASS"

    check_fail = _check_python_version(">=9.9")
    assert check_fail.status == "FAIL"
    assert check_fail.remediation == "PYTHON_VERSION_UNSUPPORTED"


def test_run_diagnostics(tmp_path: Path):
    # This will fail on VERSION and SPECIALISTS since it's an empty dir
    report = run_diagnostics(tmp_path)
    assert report.overall_status != "READY"

    version_check = next((c for c in report.checks if c.id == "VERSION"), None)
    assert version_check is not None
    assert version_check.status == "FAIL"
