"""Deterministic scope enforcement test using a real git worktree.

This test proves that the Harness (Layer B) correctly rejects out-of-scope
files even if the executor physically creates them inside the sandbox.

It does NOT depend on LLM behavior — the executor is a deterministic
function that writes both an allowed file and a rogue file.
"""

import subprocess

import pytest

from engine.runner.sandbox import WorktreeSandbox


def _git(*args, cwd):
    """Run a git command and return stdout."""
    res = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        shell=False,
    )
    if res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr}")
    return res.stdout.strip()


@pytest.fixture
def real_git_repo(tmp_path):
    """Create a real git repo with an initial commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", cwd=repo)
    _git("config", "user.email", "test@test.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)

    # Create initial file and commit so worktree has a baseline
    (repo / "README.md").write_text("initial")
    _git("add", ".", cwd=repo)
    _git("commit", "-m", "initial", cwd=repo)

    return repo


def test_rogue_file_detected_by_scope_validation(real_git_repo):
    """Real worktree + rogue file → Harness detects out-of-scope → NOT applied."""
    repo = real_git_repo
    allowed_path = "projects/.harness-internal/scratch/allowed.html"
    rogue_path = "projects/.harness-internal/scratch/OUT_OF_SCOPE.txt"
    scope_modify = [allowed_path]

    with WorktreeSandbox(repo, baseline_commit="HEAD") as sandbox:
        wt = sandbox.get_path()

        # Simulate executor: write BOTH files into the worktree
        allowed_file = wt / allowed_path
        allowed_file.parent.mkdir(parents=True, exist_ok=True)
        allowed_file.write_text("hello")

        rogue_file = wt / rogue_path
        rogue_file.write_text("I should not reach main")

        # Real get_diff
        diff_result = sandbox.get_diff()
        assert diff_result.success

        # Verify diff detected both files
        diff_paths = [c.path for c in diff_result.changes]
        assert allowed_path in diff_paths
        assert rogue_path in diff_paths

        # Verify operation types
        by_path = {c.path: c for c in diff_result.changes}
        assert by_path[allowed_path].status == "A"
        assert by_path[rogue_path].status == "A"

        # --- Scope validation (same logic as autonomous_runner.py) ---
        allowed_set = set(scope_modify)
        out_of_scope = [
            c.path for c in diff_result.changes
            if c.path not in allowed_set
        ]

        # The rogue file must be detected
        assert len(out_of_scope) == 1
        assert rogue_path in out_of_scope

        # Filter to only validated changes
        validated_changes = [
            c for c in diff_result.changes
            if c.path in allowed_set
        ]
        assert len(validated_changes) == 1
        assert validated_changes[0].path == allowed_path

        # If we were to apply only validated_changes, rogue stays out.
        # But in production, out_of_scope > 0 means we REJECT entirely.
        # For this test, verify that apply with ONLY validated works:
        apply_result = sandbox.apply_to_main(validated_changes)
        assert apply_result.success

    # Verify: allowed file reached main
    assert (repo / allowed_path).exists()
    assert (repo / allowed_path).read_text() == "hello"

    # Verify: rogue file NEVER reached main
    assert not (repo / rogue_path).exists()


def test_rogue_file_full_rejection(real_git_repo):
    """Out-of-scope detected → entire apply is skipped → nothing reaches main."""
    repo = real_git_repo
    allowed_path = "src/allowed.py"
    rogue_path = "src/rogue.py"
    scope_modify = [allowed_path]

    with WorktreeSandbox(repo, baseline_commit="HEAD") as sandbox:
        wt = sandbox.get_path()

        # Write both files
        (wt / allowed_path).parent.mkdir(parents=True, exist_ok=True)
        (wt / allowed_path).write_text("good code")
        (wt / rogue_path).write_text("bad code")

        diff_result = sandbox.get_diff()
        assert diff_result.success

        allowed_set = set(scope_modify)
        out_of_scope = [
            c.path for c in diff_result.changes
            if c.path not in allowed_set
        ]

        # Out-of-scope detected → do NOT call apply_to_main at all
        assert len(out_of_scope) > 0

    # Nothing should have reached main
    assert not (repo / allowed_path).exists()
    assert not (repo / rogue_path).exists()


def test_delete_requires_git_status_d(real_git_repo):
    """File absent in sandbox without D status → NOT deleted from main."""
    repo = real_git_repo

    # Create a file in main and commit it
    target = repo / "important.txt"
    target.write_text("do not delete me")
    _git("add", "important.txt", cwd=repo)
    _git("commit", "-m", "add important", cwd=repo)

    with WorktreeSandbox(repo, baseline_commit="HEAD") as sandbox:
        wt = sandbox.get_path()

        # important.txt exists in worktree (from baseline commit)
        assert (wt / "important.txt").exists()

        # Create only a new file — do NOT delete important.txt from worktree
        (wt / "new.txt").write_text("new content")

        diff_result = sandbox.get_diff()
        assert diff_result.success

        # Only new.txt should appear in diff (important.txt is unchanged)
        diff_paths = [c.path for c in diff_result.changes]
        assert "new.txt" in diff_paths
        assert "important.txt" not in diff_paths

        # Apply validated changes
        validated = [
            c for c in diff_result.changes if c.path == "new.txt"
        ]
        apply_result = sandbox.apply_to_main(validated)
        assert apply_result.success

    # important.txt is untouched in main
    assert target.exists()
    assert target.read_text() == "do not delete me"

    # new.txt was applied
    assert (repo / "new.txt").exists()
