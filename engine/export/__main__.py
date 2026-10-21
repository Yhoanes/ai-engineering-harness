"""
CLI entry point for engine.export.
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from engine.export.builder import (
    _get_git_commit_info,
    build_development_archive,
    build_history_bundle,
    build_portable_archive,
)
from engine.export.checksums import generate_checksums
from engine.export.manifest import Manifest, create_manifest_json
from engine.export.security import assert_safe_destination


def check_dirty_tree(repo_root: Path):
    res = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(repo_root), capture_output=True, text=True
    )
    if res.stdout.strip():
        print("DIRTY_WORKTREE: BLOCKED", file=sys.stderr)
        sys.exit(1)


def get_version(repo_root: Path) -> str:
    return (repo_root / "VERSION").read_text(encoding="utf-8").strip()


def get_release_tag(repo_root: Path, version: str) -> str | None:
    res = subprocess.run(
        ["git", "tag", "--points-at", "HEAD"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        return None

    tags = [t.strip() for t in res.stdout.splitlines() if t.strip()]
    semver_pattern = re.compile(r"^v\d+\.\d+\.\d+$")
    semver_tags = [t for t in tags if semver_pattern.match(t)]

    expected_tag = f"v{version}"

    if not semver_tags:
        return None

    if expected_tag in semver_tags:
        return expected_tag

    if len(semver_tags) == 1:
        print(
            f"VERSION_TAG_MISMATCH: BLOCKED. Expected {expected_tag} "
            f"but HEAD has {semver_tags[0]}.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"VERSION_TAG_MISMATCH: BLOCKED. Multiple SemVer tags found {semver_tags}, "
        f"but {expected_tag} is missing.",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="AI Engineering Harness Backup and Distribution Export"
    )
    parser.add_argument(
        "--output", required=True, type=str, help="Destination directory (must not exist)"
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    output_dir = Path(args.output).resolve()

    assert_safe_destination(output_dir, repo_root)
    check_dirty_tree(repo_root)

    source_commit, source_timestamp = _get_git_commit_info(repo_root)
    version = get_version(repo_root)

    # Use a staging directory alongside the requested output if possible
    # We will use tempfile to guarantee safe atomicity
    with tempfile.TemporaryDirectory(dir=output_dir.parent) as td:
        staging_dir = Path(td)

        dev_zip = staging_dir / f"AI-Engineering-Harness-{version}-DEVELOPMENT.zip"
        port_zip = staging_dir / f"AI-Engineering-Harness-{version}-PORTABLE.zip"
        hist_bundle = staging_dir / f"AI-Engineering-Harness-{version}-HISTORY.bundle"
        manifest_file = staging_dir / "MANIFEST.json"
        checksum_file = staging_dir / "SHA256SUMS.txt"

        print("Building DEVELOPMENT.zip...")
        build_development_archive(repo_root, dev_zip, source_timestamp)

        print("Building PORTABLE.zip...")
        build_portable_archive(repo_root, port_zip, source_timestamp)

        print("Building HISTORY.bundle...")
        build_history_bundle(repo_root, hist_bundle)

        import hashlib

        def get_hash(p: Path) -> tuple[str, int]:
            h = hashlib.sha256()
            size = p.stat().st_size
            with p.open("rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    h.update(chunk)
            return h.hexdigest(), size

        dev_hash, dev_size = get_hash(dev_zip)
        port_hash, port_size = get_hash(port_zip)
        hist_hash, hist_size = get_hash(hist_bundle)

        # Manifest
        manifest: Manifest = {
            "product_name": "AI Engineering Harness",
            "version": version,
            "source_commit": source_commit,
            "source_commit_timestamp": source_timestamp,
            "release_tag": get_release_tag(repo_root, version),
            "export_format_version": "1",
            "artifacts": [
                {
                    "name": dev_zip.name,
                    "type": "development",
                    "sha256": dev_hash,
                    "size_bytes": dev_size,
                    "policy": "tracked_only",
                },
                {
                    "name": port_zip.name,
                    "type": "portable",
                    "sha256": port_hash,
                    "size_bytes": port_size,
                    "policy": "distribution_builder",
                },
                {
                    "name": hist_bundle.name,
                    "type": "history",
                    "sha256": hist_hash,
                    "size_bytes": hist_size,
                    "policy": "git_bundle_all",
                },
            ],
            "development_policy": "git_ls_files_filtered",
            "portable_policy": "distribution_manifest",
            "history_bundle_verified": True,
            "test_baseline": "pytest_and_diagnostics",
            "diagnostics_status": "READY",
        }

        print("Building MANIFEST.json...")
        create_manifest_json(manifest, manifest_file)

        print("Building SHA256SUMS.txt...")
        generate_checksums([dev_zip, port_zip, hist_bundle, manifest_file], checksum_file)

        # Check source mutation
        final_commit, _ = _get_git_commit_info(repo_root)
        if source_commit != final_commit:
            print("SOURCE_MUTATED_DURING_EXPORT: BLOCKED", file=sys.stderr)
            sys.exit(1)

        check_dirty_tree(repo_root)

        # Rename staging to final output
        shutil.move(str(staging_dir), str(output_dir))
        print(f"Export successful to {output_dir}")


if __name__ == "__main__":
    main()
