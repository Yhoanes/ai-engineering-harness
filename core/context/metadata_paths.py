from __future__ import annotations

import re
from pathlib import Path


def is_valid_project_id(project_id: str) -> bool:
    """Canonical validation for project IDs."""
    return bool(re.match(r"^[a-zA-Z0-9_.-]+$", project_id)) and ".." not in project_id


def is_valid_task_id(task_id: str) -> bool:
    """Canonical validation for task IDs."""
    # Use the strictest regex from adapter for task IDs.
    return bool(re.match(r"^(TASK|HARNESS(?:-BOOTSTRAP)?)-\d{4}$", task_id))


def _do_resolve(p: Path) -> Path:
    """Helper to allow deterministic mocking of Path.resolve() in tests."""
    return p.resolve()


def resolve_safe_path(base_path: Path, rel_path: str) -> Path | None:
    """
    Resolves a path and verifies it does not escape the base_path boundary.
    Returns the resolved Path if safe, None otherwise.
    """
    resolved_base = _do_resolve(base_path)
    # Using / operator resolves the relative path. Then we resolve() it to expand .. and symlinks.
    resolved_target = _do_resolve(base_path / rel_path)

    try:
        resolved_target.relative_to(resolved_base)
        return resolved_target
    except ValueError:
        return None


class MetadataPaths:
    """
    Abstractions for resolving Harness AI metadata paths.
    This component strictly handles metadata (tasks, proposals, memory, evidence, context).
    It DOES NOT handle the project's actual source code workspace.
    """

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root)

    def _resolve_project(self, project_id: str) -> str:
        if not is_valid_project_id(project_id):
            raise ValueError(f"Invalid project format: {project_id}")
        if project_id in ("_harness-internal", ".harness-internal", "harness-internal"):
            return "harness-internal"
        return project_id

    def _has_governed_metadata(self, root: Path) -> bool:
        if not root.is_dir():
            return False
        governed = {"tasks", "proposals", "evidence", "memory", "context", "sessions"}
        for child in root.iterdir():
            if child.name in governed and child.is_dir():
                try:
                    next(child.iterdir())
                    return True
                except StopIteration:
                    pass
        return False

    def metadata_root(self, project_id: str) -> Path:
        """Root directory for all Harness metadata for a project."""
        resolved = self._resolve_project(project_id)

        if resolved == "harness-internal":
            target_new = self.repo_root / ".harness" / "projects" / "harness-internal"
            target_old = self.repo_root / "projects" / ".harness-internal"

            new_has_meta = self._has_governed_metadata(target_new)
            old_has_meta = self._has_governed_metadata(target_old)

            if new_has_meta and old_has_meta:
                raise ValueError(
                    f"Split-brain metadata detected for '{resolved}'. "
                    f"Both {target_new} and {target_old} contain governed data."
                )

            if new_has_meta:
                return _do_resolve(target_new)
            if old_has_meta:
                return _do_resolve(target_old)

            return _do_resolve(target_new)
        else:
            # Other projects remain in projects/ until a global migration is decided.
            return _do_resolve(self.repo_root / "projects" / resolved)

    def task_contract(self, project_id: str, task_id: str) -> Path:
        if not is_valid_task_id(task_id):
            raise ValueError(f"Invalid task_id format: {task_id}")
        return self.metadata_root(project_id) / "tasks" / f"{task_id}.yaml"

    def proposal(self, project_id: str, task_id: str) -> Path:
        if not is_valid_task_id(task_id):
            raise ValueError(f"Invalid task_id format: {task_id}")
        return self.metadata_root(project_id) / "proposals" / f"{task_id}.md"

    def evidence_dir(self, project_id: str, task_id: str) -> Path:
        if not is_valid_task_id(task_id):
            raise ValueError(f"Invalid task_id format: {task_id}")
        return self.metadata_root(project_id) / "evidence" / task_id

    def audit_trail(self, project_id: str, task_id: str) -> Path:
        return self.evidence_dir(project_id, task_id) / "audit_trail.jsonl"
