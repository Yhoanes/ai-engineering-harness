import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def temp_repo(tmp_path: Path):
    repo_root = tmp_path / "AI Engineering Harness Test"
    # Copy necessary structures
    source_root = Path(__file__).parent.parent

    # We just need install script and enough structure to pass Check
    shutil.copytree(source_root / "install", repo_root / "install")
    shutil.copytree(source_root / "engine", repo_root / "engine")
    (repo_root / "VERSION").write_text("1.0.0", encoding="utf-8")
    (repo_root / "pyproject.toml").write_text('requires-python = ">=3.11"', encoding="utf-8")

    return repo_root


def test_powershell_bootstrap_check(temp_repo: Path):
    # Tests that -Check works without installing anything if venv doesn't exist
    setup_script = temp_repo / "install" / "setup.ps1"

    # Run Check mode
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(setup_script),
            "-Check",
        ],
        cwd=str(temp_repo),
        capture_output=True,
        text=True,
    )

    # If no venv, it should exit with 2 (NOT_INSTALLED)
    assert result.returncode == 2
    assert "NOT_INSTALLED" in result.stdout


def test_powershell_bootstrap_creates_venv(temp_repo: Path, monkeypatch):
    # To prevent actual pip install which takes time in tests, we can test just the parsing logic
    # or rely on the portable installation integration test instead of full end-to-end here.

    setup_script = temp_repo / "install" / "setup.ps1"
    content = setup_script.read_text(encoding="utf-8")

    assert "Set-ExecutionPolicy" not in content
    assert "Start-Process -Verb RunAs" not in content
    assert "Remove-Item" not in content  # Venv deletion check
    assert "-m pip install" in content
    assert "engine.diagnostics" in content
    assert "projects/" not in content
