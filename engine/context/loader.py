from __future__ import annotations

from pathlib import Path

from core.context.metadata_paths import (
    MetadataPaths,
    is_valid_project_id,
    is_valid_task_id,
    resolve_safe_path,
)

from .models import ContextBundle

MAX_FILE_BYTES = 1024 * 1024  # 1MB
MAX_BUNDLE_BYTES = 5 * 1024 * 1024  # 5MB


def resolve_project_root(repo_root: Path, project_key: str) -> Path:
    """Legacy helper to resolve the actual project workspace root."""
    if not is_valid_project_id(project_key):
        raise ValueError(f"Invalid project_key format: {project_key}")

    # We still use the manual path resolution for backward compatibility with
    # engine.projects.manager which relies on this for the workspace root.
    resolved_target = resolve_safe_path(repo_root, f"projects/{project_key}")

    if resolved_target is None:
        raise ValueError("Project root escapes repository boundary.")

    return resolved_target


def load_context(
    repo_root: Path, project_key: str, level: int = 0, task_id: str | None = None
) -> ContextBundle:
    if level not in {0, 1, 2, 3}:
        raise ValueError("Invalid context level")

    paths = MetadataPaths(repo_root)
    # The metadata_root is explicitly used for ALL harness state
    metadata_root = paths.metadata_root(project_key)

    sources = {}
    missing = []
    contents = {}
    warnings = []

    total_bytes = 0
    targets = []

    # L0
    targets.extend([("memory/current-state.md", 0), ("memory/key-facts.md", 0)])

    # L1
    if level >= 1:
        targets.extend([("context/architecture.md", 1), ("context/active-tasks.md", 1)])

    # L2
    if level >= 2:
        if task_id:
            # We enforce strict regex on task_id to prevent path injection
            if not is_valid_task_id(task_id):
                warnings.append(f"Skipping task {task_id}: invalid format.")
            else:
                targets.extend([(f"tasks/{task_id}.yaml", 2), (f"proposals/{task_id}.md", 2)])
        else:
            warnings.append("Level 2 requested but no task_id provided. Skipping task contract.")

        # ADRs can be dynamically expanded. Using index for scope limits.
        targets.extend([("context/adrs/index.md", 2)])

    # L3
    if level == 3:
        # Load historical evidence logs
        targets.extend([("evidence/historical-index.md", 3), ("sessions/historical-index.md", 3)])

    for rel_path, _req_lvl in targets:
        p = resolve_safe_path(metadata_root, rel_path)

        if p is None:
            warnings.append(f"Skipping {rel_path}: Symlink escapes project root.")
            continue

        if not p.exists():
            missing.append(rel_path)
            continue

        if not p.is_file():
            warnings.append(f"Skipping {rel_path}: Not a file.")
            continue

        try:
            stat = p.stat()
            size = stat.st_size
            if size > MAX_FILE_BYTES:
                warnings.append(f"Skipping {rel_path}: Exceeds MAX_FILE_BYTES.")
                continue

            if total_bytes + size > MAX_BUNDLE_BYTES:
                warnings.append(f"Skipping {rel_path}: Bundle exceeds MAX_BUNDLE_BYTES.")
                continue

            data = p.read_bytes()
            if b"\x00" in data:
                warnings.append(f"Skipping {rel_path}: Appears to be binary.")
                continue

            text = data.decode("utf-8", errors="strict")
            sources[rel_path] = str(p)
            contents[rel_path] = text
            total_bytes += size

        except Exception as e:
            warnings.append(f"Skipping {rel_path}: {e}")

    return ContextBundle(
        project=project_key,
        requested_level=level,
        loaded_level=level,
        sources=sources,
        missing_sources=missing,
        content_sections=contents,
        warnings=warnings,
    )
