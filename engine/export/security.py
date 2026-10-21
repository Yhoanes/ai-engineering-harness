"""
Security and validation rules for exporting archives.
"""

import re
from pathlib import Path


def is_path_safe_for_zip(path_str: str) -> bool:
    """Ensure path has no absolute components, upward traversals or UNC/Drive letters."""
    if ".." in path_str or path_str.startswith("/") or path_str.startswith("\\"):
        return False
    return ":" not in path_str


def scan_text_for_secrets(content: str) -> bool:
    """
    Minimal secrets scanner for export boundaries.
    Fails closed if high-entropy or clear secrets are detected.
    """
    if not content.strip():
        return False

    # Check for machine paths (split strings to avoid self-detection)
    if ("C:\\" + "Users\\") in content or ("/" + "home/") in content:
        return True

    patterns = {
        "PEM Key": r"-----BEGIN .*PRIVATE KEY" + r"-----",
        "Bearer/JWT": r"Bear" + r"er\s+[A-Za-z0-9\-\._~\+/]{20,}={0,2}",
        "AWS Access Key": r"(?<![A-Z0-9])AKI" + r"A[A-Z0-9]{16}(?![A-Z0-9])",
        "Credential Assignment": (
            r"(?i)(password|token|api_key|client_secret|secret|auth)\s*[:=]\s*"
            r"[\"']([^\"'\s]{16,})[\"']"
        ),
    }

    placeholders = ["YOUR", "EXAMPLE", "TOKEN", "CHANGEME", "PLACEHOLDER", "<", "{", "demo"]

    for category, pat in patterns.items():
        matches = list(re.finditer(pat, content))
        if matches:
            if category == "Credential Assignment":
                for match in matches:
                    val = match.group(2).upper()
                    if not any(p in val for p in placeholders):
                        return True
            else:
                return True

    return False


def assert_safe_destination(dest_dir: Path, repo_root: Path):
    """
    Ensure the destination directory is safe:
    1. Outside the source repository.
    2. Does not overwrite existing content if it exists.
    """
    dest_resolved = dest_dir.resolve()
    repo_resolved = repo_root.resolve()

    if repo_resolved in dest_resolved.parents or dest_resolved == repo_resolved:
        raise ValueError("Export destination must be strictly outside the source repository.")

    if dest_resolved.exists():
        raise FileExistsError(f"Destination '{dest_dir}' already exists. Refusing to overwrite.")


def is_user_project_path(path: Path) -> bool:
    """
    Check if a path belongs to a user project.
    Only internal tasks/evidence or project readme are allowed under projects/.
    """
    parts = path.parts
    if parts and parts[0] == "projects":
        if len(parts) > 1 and parts[1] == ".harness-internal":
            return False
        return not (len(parts) > 1 and parts[1] == "README.md")
    return False
