from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path

from engine.validators import ValidationResult


def validate(
    task: dict,
    *,
    actual_paths: list[str] | None = None,
    repo_root: Path | None = None,
) -> ValidationResult:
    """Post-check: validate that actually modified files are within scope.

    Detects ALL changes after baseline:
    - Committed changes since baseline (git diff)
    - Staged but uncommitted (git diff --cached)
    - Unstaged modifications (git diff)
    - Untracked files (git ls-files --others)
    """
    errors: list[str] = []
    warnings: list[str] = []

    scope = task.get("scope", {})
    allowed_paths = scope.get("planned_paths", {}).get("modify", [])

    if not allowed_paths:
        errors.append("scope.planned_paths.modify is empty")
        return ValidationResult(
            valid=False, validator_id="validate_allowed_paths_post", errors=errors
        )

    if repo_root is None:
        repo_root = Path.cwd()

    # Use provided paths or detect from git
    if actual_paths is None:
        try:
            actual_paths = _detect_all_changes(task, repo_root)
        except ValueError as e:
            errors.append(str(e))
            return ValidationResult(
                valid=False, validator_id="validate_allowed_paths_post", errors=errors
            )

    # Filter out the task contract itself (it's expected to be modified)
    task_contract_path = _get_task_contract_path(task, repo_root)
    filtered_paths = [p for p in actual_paths if p != task_contract_path]

    out_of_scope: list[str] = []
    for actual_path in filtered_paths:
        if not _path_within_allowed(actual_path, allowed_paths):
            out_of_scope.append(actual_path)

    if out_of_scope:
        errors.append(f"Files modified outside of scope: {out_of_scope}")

    return ValidationResult(
        valid=len(errors) == 0,
        validator_id="validate_allowed_paths_post",
        errors=errors,
        warnings=warnings,
    )


def _detect_all_changes(task: dict, repo_root: Path) -> list[str]:
    """Detect all file changes since baseline using multiple git commands."""
    baseline = task.get("implementation_baseline", {})
    git_head = baseline.get("git_head")
    all_files: set[str] = set()

    if git_head:
        # 1. Committed changes since baseline
        committed = _git_command(
            ["git", "diff", "--name-only", f"{git_head}..HEAD"],
            cwd=repo_root,
        )
        all_files.update(committed)

    # 2. Staged but uncommitted
    staged = _git_command(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo_root,
    )
    all_files.update(staged)

    # 3. Unstaged modifications
    unstaged = _git_command(
        ["git", "diff", "--name-only"],
        cwd=repo_root,
    )
    all_files.update(unstaged)

    # 4. Untracked files (excluding .gitignored)
    current_untracked = _git_command(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo_root,
    )

    if git_head:
        if "preexisting_untracked" not in baseline:
            # Legacy baseline without snapshot
            if current_untracked:
                raise ValueError("Legacy baseline snapshot missing.")
        else:
            preexisting = baseline.get("preexisting_untracked") or []

            # Validate hashes and paths in baseline
            baseline_map: dict[str, str] = {}
            for item in preexisting:
                path = item.get("path")
                sha = item.get("sha256")
                if not path or not sha:
                    raise ValueError("Malformed entry: missing path or sha256.")
                if not re.match(r"^[a-f0-9]{64}$", sha):
                    raise ValueError(f"Invalid SHA-256 hash in baseline for {path}: {sha}")
                _resolve_safe_path(path, repo_root)  # Throws ValueError if unsafe
                baseline_map[path] = sha

            current_untracked_set = set(current_untracked)

            # Detect deletions (in baseline but no longer untracked)
            # Note: if an untracked file was staged/committed, it is no longer untracked
            # but WILL show up in staged/committed.
            for path in baseline_map:
                if path not in current_untracked_set:
                    all_files.add(path)

            for path in current_untracked:
                if path not in baseline_map:
                    # New untracked file
                    all_files.add(path)
                else:
                    # Preexisting untracked file. Did it change?
                    try:
                        current_sha = _calculate_sha256(path, repo_root)
                        if current_sha != baseline_map[path]:
                            all_files.add(path)
                    except Exception:
                        # If we can't hash it now, treat it as changed/error
                        all_files.add(path)
    else:
        # No baseline at all, assume all untracked are new
        all_files.update(current_untracked)

    return sorted(f for f in all_files if f)


def _git_command(cmd: list[str], cwd: Path) -> list[str]:
    """Run a git command and return output lines."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    except (OSError, subprocess.SubprocessError):
        return []


def _path_within_allowed(path: str, allowed_paths: list[str]) -> bool:
    """Check if a path matches any allowed path pattern."""
    normalized = path.replace("\\", "/")
    for pattern in allowed_paths:
        pattern_normalized = pattern.replace("\\", "/")
        if fnmatch(normalized, pattern_normalized):
            return True
        pattern_dir = pattern_normalized.rstrip("*").rstrip("/")
        if normalized.startswith(pattern_dir + "/") or normalized == pattern_dir:
            return True
        if normalized == pattern_normalized:
            return True
    return False


def _get_task_contract_path(task: dict, repo_root: Path | None = None) -> str | None:
    """Get the expected path of the task contract file."""
    repo_root = repo_root or Path.cwd()
    task_id = task.get("task_id", "")
    project = task.get("project", "")
    if not task_id or not project:
        return None

    from core.context.metadata_paths import MetadataPaths
    paths = MetadataPaths(repo_root)
    # Get relative path to repo root for consistency with other git paths
    contract_path = paths.task_contract(project, task_id)
    return contract_path.relative_to(repo_root.resolve()).as_posix()


def check_clean_working_tree(repo_root: Path | None = None) -> tuple[bool, list[str]]:
    """Check if the working tree is clean. Returns (is_clean, dirty_files)."""
    if repo_root is None:
        repo_root = Path.cwd()
    dirty = _git_command(["git", "status", "--short"], cwd=repo_root)
    return len(dirty) == 0, dirty


def _resolve_safe_path(rel_path: str, repo_root: Path) -> Path:
    """Resolves a relative path strictly within the repo root. Prevents traversal."""
    from core.context.metadata_paths import resolve_safe_path

    target = resolve_safe_path(repo_root, rel_path)
    if target is None:
        raise ValueError(f"Path traversal or absolute path detected: {rel_path}")
    return target


def _calculate_sha256(rel_path: str, repo_root: Path) -> str:
    """Calculate the SHA-256 hash of a file safely."""
    target = _resolve_safe_path(rel_path, repo_root)
    hasher = hashlib.sha256()
    with target.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def capture_baseline(repo_root: Path | None = None) -> dict:
    """Capture the current git HEAD and pre-existing untracked files as a baseline."""
    if repo_root is None:
        repo_root = Path.cwd()

    head_lines = _git_command(["git", "rev-parse", "HEAD"], cwd=repo_root)
    head = head_lines[0] if head_lines else None
    is_clean, _ = check_clean_working_tree(repo_root)

    untracked = _git_command(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo_root,
    )

    preexisting_untracked = []
    for f in sorted(untracked):
        try:
            sha = _calculate_sha256(f, repo_root)
            preexisting_untracked.append({"path": f, "sha256": sha})
        except Exception:
            # If a file is unreadable for some reason, we can't safely baseline it.
            pass

    return {
        "git_head": head,
        "working_tree_clean": is_clean,
        "captured_at": datetime.now(UTC).isoformat(),
        "preexisting_untracked": preexisting_untracked,
    }
