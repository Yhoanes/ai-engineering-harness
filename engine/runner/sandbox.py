import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SandboxChange:
    """A single file-level change detected in the sandbox."""

    status: str  # "A" (create), "M" (modify), "D" (delete), "R" (rename)
    path: str
    old_path: str | None = None  # only for renames


@dataclass
class SandboxResult:
    """Result of a sandbox diff or apply operation."""

    changes: list[SandboxChange] = field(default_factory=list)
    success: bool = True
    error: str | None = None

    @property
    def diff_files(self) -> list[str]:
        """All paths touched (backward-compat convenience)."""
        return [c.path for c in self.changes]


class StagingSandbox:
    """Sandbox for plan-task where only the contract is written."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.temp_dir = tempfile.mkdtemp(prefix="harness-staging-")

    def get_path(self) -> Path:
        return Path(self.temp_dir)

    def cleanup(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


class WorktreeSandbox:
    """Git Worktree sandbox for implement-task."""

    def __init__(self, repo_root: Path, baseline_commit: str = "HEAD"):
        self.repo_root = repo_root
        self.baseline_commit = baseline_commit
        self.temp_dir = tempfile.mkdtemp(prefix="harness-worktree-")

    def get_path(self) -> Path:
        return Path(self.temp_dir)

    def setup(self) -> None:
        cmd = ["git", "worktree", "add", self.temp_dir, self.baseline_commit]
        res = subprocess.run(
            cmd, cwd=self.repo_root, capture_output=True, text=True, shell=False
        )
        if res.returncode != 0:
            raise RuntimeError(f"Failed to create git worktree: {res.stderr}")

    def cleanup(self) -> None:
        if os.path.exists(self.temp_dir):
            cmd = ["git", "worktree", "remove", "--force", self.temp_dir]
            subprocess.run(cmd, cwd=self.repo_root, capture_output=True, shell=False)
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)

    def get_commit(self) -> str:
        cmd = ["git", "rev-parse", "HEAD"]
        res = subprocess.run(
            cmd, cwd=self.repo_root, capture_output=True, text=True, shell=False
        )
        return res.stdout.strip()

    def get_tags(self) -> set[str]:
        cmd = ["git", "tag"]
        res = subprocess.run(
            cmd, cwd=self.repo_root, capture_output=True, text=True, shell=False
        )
        return set(res.stdout.splitlines())

    def get_diff(self) -> SandboxResult:
        """Parse git status to get structured changes with operation type."""
        cmd = ["git", "status", "--porcelain", "-uall"]
        res = subprocess.run(
            cmd, cwd=self.temp_dir, capture_output=True, text=True, shell=False
        )
        if res.returncode != 0:
            return SandboxResult(success=False, error=res.stderr)

        changes: list[SandboxChange] = []
        for line in res.stdout.splitlines():
            if not line.strip():
                continue
            # Git porcelain: XY filename
            # X = index status, Y = worktree status
            xy = line[:2]
            rest = line[3:]

            status = _classify_status(xy)
            if status == "R":
                parts = rest.split(" -> ")
                old = _unquote(parts[0].strip())
                new = _unquote(parts[-1].strip())
                changes.append(SandboxChange(
                    status="R", path=new, old_path=old
                ))
            else:
                path = _unquote(rest.strip())
                changes.append(SandboxChange(status=status, path=path))

        return SandboxResult(changes=changes, success=True)

    def apply_to_main(
        self, validated_changes: list[SandboxChange]
    ) -> SandboxResult:
        """Apply validated changes with operation-specific semantics."""
        for change in validated_changes:
            sandbox_path = Path(self.temp_dir) / change.path
            main_path = self.repo_root / change.path

            if change.status in ("A", "M"):
                if not sandbox_path.exists():
                    return SandboxResult(
                        success=False,
                        error=(
                            f"{change.status} {change.path}: "
                            "file missing in sandbox"
                        ),
                    )
                main_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sandbox_path, main_path)

            elif change.status == "D":
                if not main_path.exists():
                    return SandboxResult(
                        success=False,
                        error=(
                            f"D {change.path}: "
                            "file missing in main repo"
                        ),
                    )
                main_path.unlink()

            elif change.status == "R":
                if not sandbox_path.exists():
                    return SandboxResult(
                        success=False,
                        error=(
                            f"R {change.old_path} -> {change.path}: "
                            "new file missing in sandbox"
                        ),
                    )
                old_main = self.repo_root / change.old_path
                if old_main.exists():
                    old_main.unlink()
                main_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sandbox_path, main_path)

            else:
                return SandboxResult(
                    success=False,
                    error=f"Unknown status '{change.status}' for {change.path}",
                )

        return SandboxResult(changes=validated_changes, success=True)

    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def _unquote(s: str) -> str:
    """Remove surrounding quotes if git quoted the path."""
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


def _classify_status(xy: str) -> str:
    """Map git porcelain XY codes to our A/M/D/R status."""
    x, y = xy[0], xy[1]
    if x == "R" or y == "R":
        return "R"
    if x == "D" or y == "D":
        return "D"
    if x == "A" or xy == "??":
        return "A"
    return "M"
