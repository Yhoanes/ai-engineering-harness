"""
SHA256 checksum generation for exports.
"""

import hashlib
from pathlib import Path


def generate_checksums(files: list[Path], dest: Path):
    """
    Generate SHA256SUMS.txt in standard format.
    Sorted alphabetically for determinism.
    """
    checksums = []
    for f in sorted(files, key=lambda p: p.name):
        h = hashlib.sha256()
        with f.open("rb") as content:
            # Read in chunks for large files
            for chunk in iter(lambda: content.read(4096), b""):
                h.update(chunk)
        checksums.append(f"{h.hexdigest()}  {f.name}")

    with dest.open("w", encoding="utf-8") as f:
        f.write("\n".join(checksums) + "\n")
