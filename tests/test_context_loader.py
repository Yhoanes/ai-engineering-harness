import os
from pathlib import Path

import pytest

from engine.context.loader import load_context, resolve_project_root
from engine.context.source_of_truth import SOURCE_OF_TRUTH_CLASSIFICATION, TrustLevel


def test_resolve_project_root():
    repo = Path("/mock/repo")
    expected = (repo / "projects/.harness-internal").resolve()
    assert resolve_project_root(repo, ".harness-internal") == expected
    assert resolve_project_root(repo, "analista") == (repo / "projects/analista").resolve()

    with pytest.raises(ValueError, match="Invalid project_key format"):
        resolve_project_root(repo, "../escape")

    with pytest.raises(ValueError, match="Invalid project_key format"):
        resolve_project_root(repo, "foo/bar")

    with pytest.raises(ValueError, match="Invalid project_key format"):
        resolve_project_root(repo, ".harness-internal/..")


def test_load_context_levels(tmp_path):
    project_dir = tmp_path / "projects" / "test-project"
    project_dir.mkdir(parents=True)

    (project_dir / "memory").mkdir()
    (project_dir / "memory/current-state.md").write_text("L0")

    (project_dir / "context").mkdir()
    (project_dir / "context/architecture.md").write_text("L1")

    (project_dir / "tasks").mkdir()
    (project_dir / "tasks/TASK-0001.yaml").write_text("L2")

    (project_dir / "evidence").mkdir()
    (project_dir / "evidence/historical-index.md").write_text("L3")

    # L0
    b0 = load_context(tmp_path, "test-project", level=0)
    assert "memory/current-state.md" in b0.sources
    assert "context/architecture.md" not in b0.sources

    # L1
    b1 = load_context(tmp_path, "test-project", level=1)
    assert "memory/current-state.md" in b1.sources
    assert "context/architecture.md" in b1.sources
    assert "tasks/TASK-0001.yaml" not in b1.sources

    # L2 without task_id
    b2_no_task = load_context(tmp_path, "test-project", level=2)
    assert "memory/current-state.md" in b2_no_task.sources
    assert "tasks/TASK-0001.yaml" not in b2_no_task.sources
    assert any("no task_id provided" in w for w in b2_no_task.warnings)

    # L2 with task_id
    b2 = load_context(tmp_path, "test-project", level=2, task_id="TASK-0001")
    assert "tasks/TASK-0001.yaml" in b2.sources
    assert "evidence/historical-index.md" not in b2.sources

    # L3
    b3 = load_context(tmp_path, "test-project", level=3, task_id="TASK-0001")
    assert "evidence/historical-index.md" in b3.sources


def test_source_of_truth():
    assert SOURCE_OF_TRUTH_CLASSIFICATION["conversation"] == TrustLevel.INFORMATIONAL_ONLY
    assert SOURCE_OF_TRUTH_CLASSIFICATION["conversation"] != TrustLevel.AUTHORITATIVE
    assert SOURCE_OF_TRUTH_CLASSIFICATION["conversation"] != TrustLevel.CANONICAL_REPO_STATE
    assert SOURCE_OF_TRUTH_CLASSIFICATION["git"] == TrustLevel.CANONICAL_REPO_STATE


def test_symlink_escape_integration(tmp_path):
    """Optional OS-level integration test. May skip on Windows without admin."""
    project_dir = tmp_path / "projects" / "test-project"
    project_dir.mkdir(parents=True)
    memory_dir = project_dir / "memory"
    memory_dir.mkdir()

    escape_file = tmp_path / "secret.txt"
    escape_file.write_text("secret")

    symlink_path = memory_dir / "current-state.md"
    try:
        os.symlink(escape_file, symlink_path)
        bundle = load_context(tmp_path, "test-project", level=0)
        assert "memory/current-state.md" not in bundle.sources
        assert any("Symlink escapes" in w for w in bundle.warnings)
    except OSError:
        pytest.skip("Symlinks not supported on this OS without admin privileges")


def test_symlink_escape_deterministic(monkeypatch, tmp_path):
    """Mandatory AC-24 test: Deterministically proves Path.resolve() escapes are blocked."""
    project_dir = tmp_path / "projects" / "test-project"
    project_dir.mkdir(parents=True)

    def mock_do_resolve(p: Path) -> Path:
        if "current-state.md" in p.name:
            # Simulate a canonical path resolution that points outside the project root
            return Path("/external/secret.txt")
        return p.absolute()

    monkeypatch.setattr("core.context.metadata_paths._do_resolve", mock_do_resolve)

    bundle = load_context(tmp_path, "test-project", level=0)

    assert "memory/current-state.md" not in bundle.sources
    assert any("Symlink escapes project root" in w for w in bundle.warnings)


def test_load_context_with_proposal(tmp_path):
    project_dir = tmp_path / "projects" / "test-project"
    project_dir.mkdir(parents=True)

    (project_dir / "memory").mkdir()
    (project_dir / "memory/current-state.md").write_text("L0")

    (project_dir / "tasks").mkdir()
    (project_dir / "tasks/TASK-0001.yaml").write_text("task_id: TASK-0001")

    (project_dir / "proposals").mkdir()
    (project_dir / "proposals/TASK-0001.md").write_text("# Proposal TASK-0001")
    (project_dir / "proposals/TASK-0002.md").write_text("# Proposal TASK-0002")

    bundle = load_context(tmp_path, "test-project", level=2, task_id="TASK-0001")

    assert "tasks/TASK-0001.yaml" in bundle.sources
    assert bundle.content_sections["tasks/TASK-0001.yaml"] == "task_id: TASK-0001"

    assert "proposals/TASK-0001.md" in bundle.sources
    assert bundle.content_sections["proposals/TASK-0001.md"] == "# Proposal TASK-0001"

    # Ensure other proposals are not loaded
    assert "proposals/TASK-0002.md" not in bundle.sources
    assert "proposals/TASK-0002.md" not in bundle.content_sections


def test_load_context_proposal_absent_backward_compatibility(tmp_path):
    project_dir = tmp_path / "projects" / "test-project"
    project_dir.mkdir(parents=True)

    (project_dir / "memory").mkdir()
    (project_dir / "memory/current-state.md").write_text("L0")

    (project_dir / "tasks").mkdir()
    (project_dir / "tasks/TASK-0001.yaml").write_text("task_id: TASK-0001")

    # No proposals directory or file exists
    bundle = load_context(tmp_path, "test-project", level=2, task_id="TASK-0001")

    assert "tasks/TASK-0001.yaml" in bundle.sources
    assert bundle.content_sections["tasks/TASK-0001.yaml"] == "task_id: TASK-0001"

    assert "proposals/TASK-0001.md" not in bundle.sources
    assert "proposals/TASK-0001.md" not in bundle.content_sections
    assert "proposals/TASK-0001.md" in bundle.missing_sources


def test_load_context_task_id_invalid_traversal(tmp_path):
    project_dir = tmp_path / "projects" / "test-project"
    project_dir.mkdir(parents=True)

    (project_dir / "memory").mkdir()
    (project_dir / "memory/current-state.md").write_text("L0")

    bundle = load_context(tmp_path, "test-project", level=2, task_id="../escape")
    assert any("invalid format" in w for w in bundle.warnings)
    assert "tasks/../escape.yaml" not in bundle.sources
    assert "proposals/../escape.md" not in bundle.sources
