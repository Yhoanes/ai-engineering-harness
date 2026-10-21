import os
from pathlib import Path


def _launcher_text() -> str:
    repo_root = Path(__file__).parent.parent
    launcher = repo_root / "INSTALAR.cmd"
    assert launcher.is_file(), "The root-level Windows launcher must exist"
    return launcher.read_text(encoding="utf-8").lower()


def test_launcher_resolves_setup_relative_to_itself() -> None:
    text = _launcher_text()

    assert 'cd /d "%~dp0"' in text
    assert '"%~dp0install\\setup.ps1"' in text
    assert "c:\\" not in text
    assert "c:/" not in text


def test_launcher_uses_process_scoped_powershell_bootstrap() -> None:
    text = _launcher_text()

    expected = (
        'powershell.exe -noprofile -executionpolicy bypass -file '
        '"%~dp0install\\setup.ps1" %*'
    )
    assert expected in text


def test_launcher_preserves_result_and_waits_for_user() -> None:
    text = _launcher_text()

    assert 'set "harness_exit_code=%errorlevel%"' in text
    assert "pause" in text
    assert "exit /b %harness_exit_code%" in text

def test_setup_python_version_validation(tmp_path):
    import subprocess
    repo_root = Path(__file__).parent.parent
    setup_ps1 = repo_root / "install" / "setup.ps1"

    # Create fake unsupported python (3.10)
    fake_dir = tmp_path / "fake_python"
    fake_dir.mkdir()
    (fake_dir / "python.bat").write_text("@echo off\necho 3.10")
    (fake_dir / "py.bat").write_text("@echo off\necho 3.10")

    env = os.environ.copy()
    env["PATH"] = f"{fake_dir};{env.get('PATH', '')}"

    res = subprocess.run(
        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(setup_ps1), "-Check"],
        env=env,
        capture_output=True,
        text=True
    )

    assert res.returncode == 2
    assert "PYTHON_VERSION_UNSUPPORTED" in res.stderr or "PYTHON_VERSION_UNSUPPORTED" in res.stdout

def test_setup_python_version_supported(tmp_path):
    import subprocess
    repo_root = Path(__file__).parent.parent
    setup_ps1 = repo_root / "install" / "setup.ps1"

    # Create fake supported python (3.12)
    fake_dir = tmp_path / "fake_python"
    fake_dir.mkdir()
    (fake_dir / "python.bat").write_text("@echo off\necho 3.12")
    (fake_dir / "py.bat").write_text("@echo off\necho 3.12")

    env = os.environ.copy()
    env["PATH"] = f"{fake_dir};{env.get('PATH', '')}"

    res = subprocess.run(
        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(setup_ps1), "-Check"],
        env=env,
        capture_output=True,
        text=True
    )

    # Depending on the system, it might fail later because it's not a real python,
    # but it should NOT exit with PYTHON_VERSION_UNSUPPORTED.
    assert "PYTHON_VERSION_UNSUPPORTED" not in res.stderr
    assert "PYTHON_VERSION_UNSUPPORTED" not in res.stdout
def test_setup_detects_agy_present(tmp_path):
    import subprocess
    repo_root = Path(__file__).parent.parent
    setup_ps1 = repo_root / "install" / "setup.ps1"

    fake_dir = tmp_path / "fake_bin"
    fake_dir.mkdir()
    (fake_dir / "python.bat").write_text("@echo off\necho 3.12")
    (fake_dir / "py.bat").write_text("@echo off\necho 3.12")
    (fake_dir / "agy.bat").write_text("@echo off\necho Antigravity")

    env = os.environ.copy()
    env["PATH"] = f"{fake_dir};{env.get('PATH', '')}"

    res = subprocess.run(
        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(setup_ps1), "-Check"],
        env=env,
        capture_output=True,
        text=True
    )

    assert "Antigravity CLI ........ PASS" in res.stdout

def test_setup_detects_agy_absent(tmp_path):
    import subprocess
    repo_root = Path(__file__).parent.parent
    setup_ps1 = repo_root / "install" / "setup.ps1"

    fake_dir = tmp_path / "fake_bin"
    fake_dir.mkdir()
    (fake_dir / "python.bat").write_text("@echo off\necho 3.12")
    (fake_dir / "py.bat").write_text("@echo off\necho 3.12")

    env = os.environ.copy()
    clean_path = ";".join([p for p in env.get("PATH", "").split(";") if "agy" not in p.lower()])
    env["PATH"] = f"{fake_dir};{clean_path}"

    res = subprocess.run(
        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(setup_ps1), "-Check"],
        env=env,
        capture_output=True,
        text=True
    )

    assert "Antigravity CLI ........ NOT INSTALLED" in res.stdout

def test_setup_no_agy_auto_install():
    repo_root = Path(__file__).parent.parent
    setup_ps1 = repo_root / "install" / "setup.ps1"
    content = setup_ps1.read_text(encoding="utf-8").lower()

    assert "curl" not in content
    assert "invoke-webrequest" not in content
    assert "winget" not in content
    assert "choco" not in content
    assert "pip install agy" not in content
