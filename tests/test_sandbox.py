import os
from unittest.mock import MagicMock, patch

from engine.runner.sandbox import (
    SandboxChange,
    SandboxResult,
    StagingSandbox,
    WorktreeSandbox,
)


def test_staging_sandbox(tmp_path):
    with StagingSandbox(tmp_path) as sandbox:
        path = sandbox.get_path()
        assert path.exists()
        assert path.is_dir()
    # After exit, it should be cleaned up
    assert not path.exists()


@patch("subprocess.run")
def test_worktree_sandbox_setup_cleanup(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)

    with WorktreeSandbox(tmp_path) as sandbox:
        path = sandbox.get_path()
        assert mock_run.call_count == 1
        args = mock_run.call_args[0][0]
        assert args[:3] == ["git", "worktree", "add"]
        assert args[3] == str(path)
        assert args[4] == "HEAD"

    # Cleanup calls git worktree remove
    assert mock_run.call_count == 2
    args2 = mock_run.call_args[0][0]
    assert args2[:3] == ["git", "worktree", "remove"]
    assert args2[4] == str(path)


@patch("subprocess.run")
def test_worktree_sandbox_get_diff(mock_run, tmp_path):
    sandbox = WorktreeSandbox(tmp_path)
    sandbox.temp_dir = str(tmp_path)

    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = (
        " M modified.py\n"
        "?? created.py\n"
        " D deleted.py\n"
        "R  old.py -> new.py\n"
    )
    mock_run.return_value = mock_res

    res = sandbox.get_diff()
    assert res.success

    by_path = {c.path: c for c in res.changes}

    assert "modified.py" in by_path
    assert by_path["modified.py"].status == "M"

    assert "created.py" in by_path
    assert by_path["created.py"].status == "A"

    assert "deleted.py" in by_path
    assert by_path["deleted.py"].status == "D"

    assert "new.py" in by_path
    assert by_path["new.py"].status == "R"
    assert by_path["new.py"].old_path == "old.py"

    # Backward compat
    assert "modified.py" in res.diff_files
    assert "new.py" in res.diff_files


# --- apply_to_main tests with real filesystem ---


def test_apply_create(tmp_path):
    """A new.txt → copied to main."""
    repo = tmp_path / "repo"
    repo.mkdir()
    sandbox = WorktreeSandbox(repo)
    sandbox.temp_dir = str(tmp_path / "wt")
    os.makedirs(sandbox.temp_dir)

    (tmp_path / "wt" / "new.txt").write_text("hello")

    changes = [SandboxChange(status="A", path="new.txt")]
    res = sandbox.apply_to_main(changes)
    assert res.success
    assert (repo / "new.txt").read_text() == "hello"


def test_apply_modify(tmp_path):
    """M existing.txt → updated in main."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "existing.txt").write_text("old")

    sandbox = WorktreeSandbox(repo)
    sandbox.temp_dir = str(tmp_path / "wt")
    os.makedirs(sandbox.temp_dir)
    (tmp_path / "wt" / "existing.txt").write_text("new")

    changes = [SandboxChange(status="M", path="existing.txt")]
    res = sandbox.apply_to_main(changes)
    assert res.success
    assert (repo / "existing.txt").read_text() == "new"


def test_apply_delete(tmp_path):
    """D old.txt → removed from main."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "old.txt").write_text("bye")

    sandbox = WorktreeSandbox(repo)
    sandbox.temp_dir = str(tmp_path / "wt")
    os.makedirs(sandbox.temp_dir)

    changes = [SandboxChange(status="D", path="old.txt")]
    res = sandbox.apply_to_main(changes)
    assert res.success
    assert not (repo / "old.txt").exists()


def test_apply_rename(tmp_path):
    """R old.txt -> new.txt → old removed, new copied."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "old.txt").write_text("content")

    sandbox = WorktreeSandbox(repo)
    sandbox.temp_dir = str(tmp_path / "wt")
    os.makedirs(sandbox.temp_dir)
    (tmp_path / "wt" / "new.txt").write_text("content")

    changes = [SandboxChange(status="R", path="new.txt", old_path="old.txt")]
    res = sandbox.apply_to_main(changes)
    assert res.success
    assert not (repo / "old.txt").exists()
    assert (repo / "new.txt").read_text() == "content"


def test_apply_missing_create_fails(tmp_path):
    """A file.txt but file missing in sandbox → failure."""
    repo = tmp_path / "repo"
    repo.mkdir()
    sandbox = WorktreeSandbox(repo)
    sandbox.temp_dir = str(tmp_path / "wt")
    os.makedirs(sandbox.temp_dir)

    changes = [SandboxChange(status="A", path="ghost.txt")]
    res = sandbox.apply_to_main(changes)
    assert not res.success
    assert "ghost.txt" in res.error
    assert "missing in sandbox" in res.error


def test_apply_delete_without_git_status_fails(tmp_path):
    """File absent in sandbox without D status → NOT deleted from main."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "keep.txt").write_text("important")

    sandbox = WorktreeSandbox(repo)
    sandbox.temp_dir = str(tmp_path / "wt")
    os.makedirs(sandbox.temp_dir)
    # File is not in sandbox, but we DON'T pass status=D
    # There's no SandboxChange for it at all
    # So nothing should happen to keep.txt
    changes: list[SandboxChange] = []
    res = sandbox.apply_to_main(changes)
    assert res.success
    # keep.txt is untouched
    assert (repo / "keep.txt").read_text() == "important"


def test_sandbox_result_error_field():
    """Canonical field is 'error'."""
    r = SandboxResult(success=False, error="something broke")
    assert r.error == "something broke"
    assert not r.success
    assert r.diff_files == []

    r2 = SandboxResult(
        changes=[SandboxChange(status="A", path="a.py")],
        success=True,
    )
    assert r2.error is None
    assert r2.success
    assert r2.diff_files == ["a.py"]


def test_sandbox_change_fields():
    """SandboxChange preserves status, path, old_path."""
    c1 = SandboxChange(status="A", path="new.py")
    assert c1.old_path is None

    c2 = SandboxChange(status="R", path="new.py", old_path="old.py")
    assert c2.old_path == "old.py"
    assert c2.status == "R"
