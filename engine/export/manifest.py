"""
Export manifest definition.
"""

import json
from pathlib import Path
from typing import TypedDict


class ArtifactMetadata(TypedDict):
    name: str
    type: str
    sha256: str
    size_bytes: int
    policy: str


class Manifest(TypedDict):
    product_name: str
    version: str
    source_commit: str
    source_commit_timestamp: int
    release_tag: str | None
    export_format_version: str
    artifacts: list[ArtifactMetadata]
    development_policy: str
    portable_policy: str
    history_bundle_verified: bool
    test_baseline: str
    diagnostics_status: str


def create_manifest_json(manifest: Manifest, dest: Path):
    with dest.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
