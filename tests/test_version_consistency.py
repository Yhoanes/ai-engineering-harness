import re
from pathlib import Path

import tomllib


def test_version_consistency():
    repo_root = Path(__file__).parent.parent

    # 1. Read VERSION file
    version_file = repo_root / "VERSION"
    assert version_file.exists(), "VERSION file must exist"
    version_text = version_file.read_text(encoding="utf-8").strip()

    # 2. Validate SemVer format
    semver_pattern = re.compile(r"^\d+\.\d+\.\d+$")
    assert semver_pattern.match(version_text), (
        f"VERSION '{version_text}' must be strict SemVer X.Y.Z"
    )

    # 3. Read pyproject.toml
    pyproject_file = repo_root / "pyproject.toml"
    assert pyproject_file.exists(), "pyproject.toml must exist"
    pyproject_data = tomllib.loads(pyproject_file.read_text(encoding="utf-8"))

    project_version = pyproject_data.get("project", {}).get("version")
    assert project_version is not None, "pyproject.toml must declare [project] version"

    # 4. Confirm exact equality
    assert version_text == project_version, (
        f"Version inconsistency detected: "
        f"VERSION says '{version_text}', but pyproject.toml says '{project_version}'."
    )
