import re
from pathlib import Path
from typing import Any

from engine.evolution.models import ExtensionType

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def validate_extension_id(extension_id: str) -> bool:
    """Validate extension ID format to prevent path traversal and enforce standard naming."""
    if not extension_id or not isinstance(extension_id, str):
        return False
    if "\0" in extension_id or "/" in extension_id or "\\" in extension_id:
        return False
    return bool(ID_PATTERN.match(extension_id))


class ExtensionRegistry:
    """Metadata-only registry for discovering Harness extensions."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def discover_all(self) -> dict[str, dict[str, Any]]:
        """Discover all extensions across standard locations."""
        registry = {}
        self._merge(registry, self._discover_specialists())
        self._merge(registry, self._discover_skills())
        return registry

    def _merge(self, target: dict[str, Any], source: dict[str, Any]) -> None:
        for k, v in source.items():
            if k in target:
                raise ValueError(f"Duplicate extension ID detected: {k}")
            target[k] = v

    def _discover_specialists(self) -> dict[str, dict[str, Any]]:
        results = {}
        spec_dir = self.repo_root / "core" / "specialists"
        if spec_dir.exists():
            for child in spec_dir.iterdir():
                if child.is_dir() and validate_extension_id(child.name):
                    results[child.name] = {
                        "type": ExtensionType.SPECIALIST,
                        "path": str(child.relative_to(self.repo_root)),
                    }
        return results

    def _discover_skills(self) -> dict[str, dict[str, Any]]:
        results = {}
        skills_dir = self.repo_root / "skills"
        if skills_dir.exists():
            for child in skills_dir.iterdir():
                # Strictly metadata-only. No execution.
                if (
                    child.is_dir()
                    and not child.name.startswith("_")
                    and validate_extension_id(child.name)
                ):
                    results[child.name] = {
                        "type": ExtensionType.SKILL,
                        "path": str(child.relative_to(self.repo_root)),
                    }
        return results
