import pytest

from core.context.metadata_paths import (
    MetadataPaths,
    is_valid_project_id,
    is_valid_task_id,
    resolve_safe_path,
)


def test_is_valid_project_id():
    assert is_valid_project_id("analista")
    assert is_valid_project_id(".harness-internal")
    assert is_valid_project_id("_harness-internal")
    assert not is_valid_project_id("../escape")
    assert not is_valid_project_id("a/b")
    assert not is_valid_project_id("a\\b")


def test_is_valid_task_id():
    assert is_valid_task_id("TASK-0001")
    assert is_valid_task_id("HARNESS-0025")
    assert not is_valid_task_id("task-0001")
    assert not is_valid_task_id("../escape")


def test_resolve_safe_path(tmp_path):
    base = tmp_path / "base"
    base.mkdir()

    # Safe resolution
    assert resolve_safe_path(base, "file.txt") == (base / "file.txt").resolve()

    # Traversal escape
    assert resolve_safe_path(base, "../escape.txt") is None

    # Absolute escape
    assert resolve_safe_path(base, "/etc/passwd") is None


def test_metadata_paths_fallback(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    paths = MetadataPaths(repo)

    # Legacy empty/non-existent defaults to NEW
    internal = paths.metadata_root(".harness-internal")
    assert internal == (repo / ".harness" / "projects" / "harness-internal").resolve()

    # Legacy alias empty/non-existent defaults to NEW
    legacy = paths.metadata_root("_harness-internal")
    assert legacy == (repo / ".harness" / "projects" / "harness-internal").resolve()

    clean = paths.metadata_root("harness-internal")
    assert clean == (repo / ".harness" / "projects" / "harness-internal").resolve()

    # Normal project
    analista = paths.metadata_root("analista")
    assert analista == (repo / "projects" / "analista").resolve()

    # Create LEGACY metadata
    legacy_root = repo / "projects" / ".harness-internal"
    legacy_root.mkdir(parents=True)
    legacy_tasks = legacy_root / "tasks"
    legacy_tasks.mkdir()
    (legacy_tasks / "foo.yaml").touch()

    # Now it should resolve to LEGACY
    assert paths.metadata_root(".harness-internal") == legacy_root.resolve()

    # Create NEW metadata
    new_root = repo / ".harness" / "projects" / "harness-internal"
    new_root.mkdir(parents=True)
    new_tasks = new_root / "tasks"
    new_tasks.mkdir()
    (new_tasks / "bar.yaml").touch()

    # SPLIT BRAIN
    with pytest.raises(ValueError, match="Split-brain"):
        paths.metadata_root(".harness-internal")

    # Remove LEGACY metadata
    (legacy_tasks / "foo.yaml").unlink()
    # Still exists, but empty. Should resolve to NEW!
    assert paths.metadata_root(".harness-internal") == new_root.resolve()

    # Tasks and proposals (using NEW)
    task = paths.task_contract("analista", "TASK-0001")
    assert task == (repo / "projects" / "analista" / "tasks" / "TASK-0001.yaml").resolve()

    proposal = paths.proposal("analista", "TASK-0001")
    assert proposal == (repo / "projects" / "analista" / "proposals" / "TASK-0001.md").resolve()

    # Evidence and audit
    evidence = paths.evidence_dir("analista", "TASK-0001")
    assert evidence == (repo / "projects" / "analista" / "evidence" / "TASK-0001").resolve()

    audit = paths.audit_trail("analista", "TASK-0001")
    expected_audit = repo / "projects" / "analista" / "evidence" / "TASK-0001" / "audit_trail.jsonl"
    assert audit == expected_audit.resolve()

    # Invalid project ID
    with pytest.raises(ValueError, match="Invalid project format"):
        paths.metadata_root("../escape")

    # Invalid task ID
    with pytest.raises(ValueError, match="Invalid task_id format"):
        paths.task_contract("analista", "../escape")
