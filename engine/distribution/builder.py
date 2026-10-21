import re
import shutil
import tempfile
from pathlib import Path

import yaml

from engine.distribution.models import DistributionManifest


def load_manifest(manifest_path: Path) -> DistributionManifest:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    with manifest_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return DistributionManifest(
        include=data.get("include", []),
        exclude_defensive=data.get("exclude_defensive", []),
        generated=data.get("generated", []),
    )


def validate_manifest(manifest: DistributionManifest):
    if not manifest.include:
        raise ValueError("Manifest has no include list.")


def _is_excluded(path: Path, excludes: list[str]) -> bool:
    return any(path.match(pat) or any(p.match(pat) for p in path.parents) for pat in excludes)


def _scan_secrets_and_machine_paths(content: str) -> tuple[bool, str]:
    # Check for machine paths (split strings to avoid self-detection)
    if ("C:\\" + "Users\\") in content or ("/" + "home/") in content:
        return True, "Machine path detected"

    # Placeholders to ignore
    placeholders = ["YOUR", "EXAMPLE", "TOKEN", "CHANGEME", "PLACEHOLDER", "<", "{", "demo"]

    # Regexes for secrets
    patterns = {
        "PEM Key": r"-----BEGIN .*PRIVATE KEY" + r"-----",
        "Bearer/JWT": r"Bear" + r"er\s+[A-Za-z0-9\-\._~\+/]{20,}={0,2}",
        "AWS Access Key": r"(?<![A-Z0-9])AKI" + r"A[A-Z0-9]{16}(?![A-Z0-9])",
        "Credential Assignment": (
            r"(?i)(password|token|api_key|client_secret|secret|auth)\s*[:=]\s*"
            r"[\"']([^\"'\s]{16,})[\"']"
        ),
    }

    for category, pat in patterns.items():
        matches = re.finditer(pat, content)
        for match in matches:
            val = match.group(0)
            val_upper = val.upper()
            is_placeholder = any(p in val_upper for p in placeholders)
            if not is_placeholder:
                return True, category

    return False, ""


def build_distribution(repo_root: Path, output_dir: Path, manifest: DistributionManifest):
    if output_dir.exists():
        raise FileExistsError(f"Destination {output_dir} already exists. Refusing to overwrite.")

    staging_dir_str = tempfile.mkdtemp(prefix="harness-pkg-staging-", dir=str(output_dir.parent))
    staging_dir = Path(staging_dir_str)

    try:
        # Allowlist copy
        for pat in manifest.include:
            for src in repo_root.glob(pat):
                if _is_excluded(src, manifest.exclude_defensive):
                    continue

                # Check symlink
                if src.is_symlink():
                    raise ValueError(
                        f"Symlink encountered at {src}. Symlinks are rejected by policy."
                    )

                rel = src.relative_to(repo_root)
                dst = staging_dir / rel

                if src.is_file():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    # Verify text files for secrets
                    try:
                        content = src.read_text(encoding="utf-8")
                        has_secret, category = _scan_secrets_and_machine_paths(content)
                        if has_secret:
                            raise ValueError(f"Security violation ({category}) detected in {src}")
                    except UnicodeDecodeError:
                        pass  # Binary file

                    shutil.copy2(src, dst)
                elif src.is_dir():
                    dst.mkdir(parents=True, exist_ok=True)
                    for item in src.rglob("*"):
                        if _is_excluded(item, manifest.exclude_defensive):
                            continue
                        if item.is_symlink():
                            raise ValueError(
                                f"Symlink encountered at {item}. Symlinks are rejected by policy."
                            )

                        item_rel = item.relative_to(repo_root)
                        item_dst = staging_dir / item_rel
                        if item.is_file():
                            item_dst.parent.mkdir(parents=True, exist_ok=True)
                            try:
                                content = item.read_text(encoding="utf-8")
                                has_secret, category = _scan_secrets_and_machine_paths(content)
                                if has_secret:
                                    raise ValueError(
                                        f"Security violation ({category}) detected in {item}"
                                    )
                            except UnicodeDecodeError:
                                pass
                            shutil.copy2(item, item_dst)
                        elif item.is_dir():
                            item_dst.mkdir(parents=True, exist_ok=True)

        # Generate files
        if "projects/README.md" in manifest.generated:
            proj_readme_src = repo_root / "packaging" / "templates" / "projects-README.md"
            if proj_readme_src.exists():
                proj_dst = staging_dir / "projects"
                proj_dst.mkdir(parents=True, exist_ok=True)
                shutil.copy2(proj_readme_src, proj_dst / "README.md")

        # Atomic Rename
        if output_dir.exists():
            raise FileExistsError("Output directory created concurrently.")
        staging_dir.rename(output_dir)

    except Exception as e:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise e


def validate_distribution(output_dir: Path):
    required = [
        "core",
        "engine",
        "adapters",
        "templates",
        "docs",
        "install",
        "projects/README.md",
        "INSTALAR.cmd",
        "README.md",
        "VERSION",
        "pyproject.toml",
        ".agents/agents.md",
        ".agents/rules/harness-governance.md",
        ".agents/skills/harness-advisor/SKILL.md",
        ".agents/workflows/advisor.md",
        ".agents/workflows/new-project.md",
        ".agents/workflows/evolve-harness.md",
    ]
    forbidden = [
        ".git",
        ".venv",
        ".harness",
        "projects/.harness-internal",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        "htmlcov",
    ]

    for req in required:
        if not (output_dir / req).exists():
            raise ValueError(f"Missing required distribution item: {req}")

    for fbd in forbidden:
        if (output_dir / fbd).exists() or list(output_dir.rglob(fbd)):
            raise ValueError(f"Forbidden distribution item found: {fbd}")
