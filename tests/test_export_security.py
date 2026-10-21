from pathlib import Path

import pytest

from engine.export.security import (
    assert_safe_destination,
    is_path_safe_for_zip,
    is_user_project_path,
    scan_text_for_secrets,
)


def test_is_path_safe_for_zip():
    assert is_path_safe_for_zip("core/main.py")
    assert not is_path_safe_for_zip("../core/main.py")
    assert not is_path_safe_for_zip("/etc/passwd")
    assert not is_path_safe_for_zip("C:\\Windows")


def test_scan_text_for_secrets():
    aws_key = "AKIA" + "1234567890123456"
    assert scan_text_for_secrets(f"API_KEY = '{aws_key}'")
    assert not scan_text_for_secrets("password = 'YOUR_PASSWORD'")
    bad = "C:" + chr(92) + "Users" + chr(92) + "Admin"
    assert scan_text_for_secrets(f"path = '{bad}'")
    assert not scan_text_for_secrets("normal code here")

    assert scan_text_for_secrets("-----BEGIN " + "RSA PRIVATE " + "KEY-----")
    jwt_str = (
        "Bear" + "er eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwi"
    )
    assert scan_text_for_secrets(f"Authorization: {jwt_str}")

    val = "1234567890123456"
    assert scan_text_for_secrets(f"password = '{val}'")
    assert scan_text_for_secrets(f"client_secret = '{val}'")


def test_is_user_project_path():
    assert not is_user_project_path(Path("projects/.harness-internal/tasks/1.yaml"))
    assert not is_user_project_path(Path(".harness/projects/harness-internal/tasks/1.yaml"))
    assert not is_user_project_path(Path("projects/README.md"))
    assert is_user_project_path(Path("projects/my-cool-app/app.py"))


def test_assert_safe_destination(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    safe_dest = tmp_path / "output"

    # Should not raise
    assert_safe_destination(safe_dest, repo)

    # Inside repo should raise
    with pytest.raises(ValueError):
        assert_safe_destination(repo / "out", repo)

    # Same as repo should raise
    with pytest.raises(ValueError):
        assert_safe_destination(repo, repo)

    # Existing destination should raise
    safe_dest.mkdir()
    with pytest.raises(FileExistsError):
        assert_safe_destination(safe_dest, repo)
