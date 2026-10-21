"""
Builder logic for DEVELOPMENT.zip, PORTABLE.zip, and HISTORY.bundle.
"""

import subprocess
import zipfile
from pathlib import Path

from engine.distribution.builder import build_distribution, load_manifest
from engine.export.security import is_path_safe_for_zip, is_user_project_path, scan_text_for_secrets


def _get_git_commit_info(repo_root: Path) -> tuple[str, int]:
    res = subprocess.run(
        ["git", "log", "-1", "--format=%H|%ct"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    out = res.stdout.strip().split("|")
    return out[0], int(out[1])


def _get_tracked_files(repo_root: Path) -> list[str]:
    res = subprocess.run(
        ["git", "ls-files"], cwd=str(repo_root), capture_output=True, text=True, check=True
    )
    return [f for f in res.stdout.splitlines() if f]


def build_development_archive(repo_root: Path, dest_zip: Path, commit_timestamp: int):
    tracked = _get_tracked_files(repo_root)

    # 1980-01-01 tuple for ZIP determinism
    zip_time = (1980, 1, 1, 0, 0, 0)

    with zipfile.ZipFile(dest_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(tracked):
            if f.startswith(".venv/") or f == ".venv":
                continue
            if ".pytest_cache" in f or ".ruff_cache" in f or "__pycache__" in f:
                continue

            p = repo_root / f

            if is_user_project_path(Path(f)):
                continue

            if not p.is_file():
                continue

            if p.is_symlink():
                raise ValueError(f"Symlinks not allowed in export: {f}")

            if not is_path_safe_for_zip(f):
                raise ValueError(f"Unsafe path detected: {f}")

            # Scan text files for secrets
            try:
                content = p.read_text(encoding="utf-8")
                # Exclude internal evidence logs from machine path checks,
                # but secrets are strictly scanned
                if scan_text_for_secrets(content):
                    raise ValueError(
                        f"Security scan failed for {f}: High entropy or secret detected."
                    )
            except UnicodeDecodeError:
                pass  # Binary file

            zi = zipfile.ZipInfo(f, zip_time)
            zi.external_attr = 0o644 << 16

            with p.open("rb") as src:
                zf.writestr(zi, src.read())


def build_portable_archive(repo_root: Path, dest_zip: Path, commit_timestamp: int):
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        temp_dist = Path(td) / "dist"
        manifest_path = repo_root / "packaging" / "distribution-manifest.yaml"
        manifest = load_manifest(manifest_path)
        build_distribution(repo_root, temp_dist, manifest)

        # Now zip deterministically
        zip_time = (1980, 1, 1, 0, 0, 0)
        with zipfile.ZipFile(dest_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            files = []
            for item in temp_dist.rglob("*"):
                if item.is_file():
                    if item.is_symlink():
                        raise ValueError(f"Symlinks not allowed in Portable export: {item}")
                    files.append(item.relative_to(temp_dist).as_posix())

            for f in sorted(files):
                if not is_path_safe_for_zip(f):
                    raise ValueError(f"Unsafe path in portable build: {f}")

                # Distribution builder already scanned for secrets, but we do one last sanity check
                p = temp_dist / f
                try:
                    content = p.read_text(encoding="utf-8")
                    if scan_text_for_secrets(content):
                        raise ValueError(f"Portable security scan failed for {f}")
                except UnicodeDecodeError:
                    pass

                zi = zipfile.ZipInfo(f, zip_time)
                zi.external_attr = 0o644 << 16
                with p.open("rb") as src:
                    zf.writestr(zi, src.read())


def build_history_bundle(repo_root: Path, dest_bundle: Path):
    res = subprocess.run(
        ["git", "bundle", "create", str(dest_bundle.resolve()), "--all"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Git bundle creation failed: {res.stderr}")
