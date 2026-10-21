import contextlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from engine.distribution.builder import (
    _scan_secrets_and_machine_paths,
    build_distribution,
    validate_distribution,
)
from engine.distribution.models import DistributionManifest


@pytest.fixture
def repo_env(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    # Fake core files
    (repo / "core").mkdir()
    (repo / "core" / "test.py").write_text("print('core')", encoding="utf-8")

    # Fake engine for isolated tests (if needed locally inside repo)
    (repo / "engine").mkdir()
    (repo / "engine" / "__init__.py").write_text("", encoding="utf-8")

    # Caches
    (repo / "core" / "__pycache__").mkdir()
    (repo / "core" / "__pycache__" / "test.pyc").write_bytes(b"00")

    # Internal project
    (repo / "projects").mkdir()
    (repo / "projects" / ".harness-internal").mkdir()
    (repo / "projects" / ".harness-internal" / "tasks").mkdir()
    (repo / "projects" / ".harness-internal" / "tasks" / "test.yaml").write_text(
        "...", encoding="utf-8"
    )

    # User project
    (repo / "projects" / "userproj").mkdir()
    (repo / "projects" / "userproj" / "README.md").write_text("user", encoding="utf-8")

    # Symlink if OS supports
    with contextlib.suppress(OSError):
        os.symlink(repo / "core", repo / "core_link")

    (repo / "packaging" / "templates").mkdir(parents=True)
    (repo / "packaging" / "templates" / "projects-README.md").write_text(
        "Clean workspace", encoding="utf-8"
    )

    return repo


def test_secret_scanner():
    # 1. Real secret rejected
    real_assignment = "API_KEY = 'AKIA1234" + "567890123456'"
    has_secret, cat = _scan_secrets_and_machine_paths(real_assignment)
    assert has_secret
    assert cat == "AWS Access Key"

    # 2. Placeholder accepted
    placeholder = "API_KEY = 'YOUR_API_KEY_HERE'"
    has_secret, _ = _scan_secrets_and_machine_paths(placeholder)
    assert not has_secret

    placeholder2 = "Bearer <TOKEN>"
    has_secret, _ = _scan_secrets_and_machine_paths(placeholder2)
    assert not has_secret

    # 3. Documentation mentioning secret
    docs = "This is a secret system that protects data."
    has_secret, _ = _scan_secrets_and_machine_paths(docs)
    assert not has_secret

    # 4. PEM rejected
    pem = "-----BEGIN RSA PRIVATE KEY" + "-----\nMIIEowIBAAKCAQEA..."
    has_secret, cat = _scan_secrets_and_machine_paths(pem)
    assert has_secret
    assert cat == "PEM Key"

    # 5. Obvious assignment rejected
    assign = "password = 'super_secret" + "_password_123!'"
    has_secret, cat = _scan_secrets_and_machine_paths(assign)
    assert has_secret
    assert cat == "Credential Assignment"


def test_machine_path_rejection(repo_env, tmp_path):
    if (repo_env / "core_link").exists():
        (repo_env / "core_link").unlink()

    # Inject machine path
    bad_path = "C:\\" + "Users\\Example\\Code"
    (repo_env / "core" / "bad.py").write_text(bad_path, encoding="utf-8")

    manifest = DistributionManifest(include=["core/**"], exclude_defensive=[], generated=[])

    out = tmp_path / "dist"
    with pytest.raises(ValueError, match="Machine path detected"):
        build_distribution(repo_env, out, manifest)

    assert not out.exists()  # Cleaned up on fail


def test_distribution_allowlist(repo_env, tmp_path):
    if (repo_env / "core_link").exists():
        (repo_env / "core_link").unlink()  # Remove symlink for clean run

    manifest = DistributionManifest(
        include=["core/**", "packaging/**"],
        exclude_defensive=["__pycache__", "projects/.harness-internal/**", "projects/*/**"],
        generated=["projects/README.md"],
    )

    out = tmp_path / "dist"
    build_distribution(repo_env, out, manifest)

    assert out.exists()
    assert (out / "core" / "test.py").exists()
    assert not (out / "core" / "__pycache__").exists()
    assert not (out / "projects" / "userproj").exists()
    assert not (out / "projects" / ".harness-internal").exists()
    assert (out / "projects" / "README.md").read_text(encoding="utf-8") == "Clean workspace"


def test_symlink_rejection(repo_env, tmp_path):
    if not (repo_env / "core_link").exists():
        pytest.skip("Symlinks not supported on this OS")

    manifest = DistributionManifest(include=["core_link/**"], exclude_defensive=[], generated=[])

    out = tmp_path / "dist"
    with pytest.raises(ValueError, match="Symlink encountered"):
        build_distribution(repo_env, out, manifest)

    assert not out.exists()  # Cleaned up on fail


def test_no_overwrite(repo_env, tmp_path):
    if (repo_env / "core_link").exists():
        (repo_env / "core_link").unlink()

    manifest = DistributionManifest(include=["core/**"], exclude_defensive=[], generated=[])

    out = tmp_path / "dist"
    out.mkdir()  # Pre-exists

    with pytest.raises(FileExistsError):
        build_distribution(repo_env, out, manifest)


def test_validate_distribution(tmp_path):
    out = tmp_path / "dist"
    out.mkdir()

    with pytest.raises(ValueError, match="Missing required"):
        validate_distribution(out)

    # Mock valid
    for req in [
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
    ]:
        p = out / req
        p.parent.mkdir(parents=True, exist_ok=True)
        if req.endswith(".md") or req.endswith(".toml") or req == "VERSION":
            p.write_text("ok", encoding="utf-8")
        else:
            p.mkdir(exist_ok=True)

    validate_distribution(out)  # Should pass now

    # Add forbidden
    (out / ".git").mkdir()
    with pytest.raises(ValueError, match="Forbidden distribution"):
        validate_distribution(out)


def test_portable_smoke_end_to_end(tmp_path):
    # This test builds a real distribution from the current repo and tests it in a clean subprocess
    repo_root = Path(__file__).resolve().parent.parent
    if not (repo_root / "packaging" / "distribution-manifest.yaml").exists():
        pytest.skip("No distribution manifest found in dev repo.")

    out = tmp_path / "dist"
    from engine.distribution.builder import build_distribution, load_manifest

    manifest = load_manifest(repo_root / "packaging" / "distribution-manifest.yaml")

    # Exclude internal projects and caches, but we still build from the real repo!
    build_distribution(repo_root, out, manifest)

    # Create the smoke script inside the distribution
    smoke_script = out / "smoke.py"
    script_content = """
import sys
from pathlib import Path
import json

# Ensure we are importing from the portable package
import engine
engine_file = engine.__file__
if not engine_file.startswith(str(Path(__file__).parent)):
    print(json.dumps({"error": f"Import leakage! engine loaded from {engine_file}"}))
    sys.exit(1)

try:
    from engine.projects.manager import initialize_project
    from engine.projects.models import ProjectDefinition
    from engine.context.loader import load_context
    from engine.advisor.service import (
        discover_specialists,
        discover_workflows,
        get_general_guidance,
    )

    repo_root = Path(__file__).parent

    # Test catalog discovery
    specs = discover_specialists(repo_root)
    wfs = discover_workflows(repo_root)

    # Initialize generic project
    pdef = ProjectDefinition("portable-smoke", "Smoke Test", "Testing portable dist")
    initialize_project(repo_root, pdef)

    # Verify initial structure
    r_md = (repo_root / "projects" / "portable-smoke" / "requirements" / "README.md").read_text()
    if "STATUS: NOT_DEFINED" not in r_md: raise Exception("Invalid requirements marker")

    a_md = (repo_root / "projects" / "portable-smoke" / "architecture" / "README.md").read_text()
    if "STATUS: NOT_DEFINED" not in a_md: raise Exception("Invalid architecture marker")

    s_md = (repo_root / "projects" / "portable-smoke" / "source" / "README.md").read_text()
    if "STATUS: NOT_INITIALIZED" not in s_md: raise Exception("Invalid source marker")

    # Context Loader Level 0
    ctx = load_context(repo_root, "portable-smoke", level=0)

    # Advisor
    adv = get_general_guidance(repo_root, "portable-smoke")
    print(json.dumps({
        "engine_file": engine_file,
        "specialists_count": len(specs),
        "workflows_count": len(wfs),
        "context_files_loaded": list(ctx.sources.keys()),
        "lifecycle_state": adv.lifecycle_state,
        "recommended_workflow": adv.recommended_workflow
    }))
except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)
"""
    smoke_script.write_text(script_content, encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(out)

    res = subprocess.run(
        [sys.executable, str(smoke_script)], cwd=str(out), env=env, capture_output=True, text=True
    )
    assert res.returncode == 0, f"Smoke script failed: {res.stderr}\nSTDOUT: {res.stdout}"

    data = json.loads(res.stdout)
    assert "error" not in data, data["error"]

    # Verify the assertions
    assert data["engine_file"].startswith(str(out)), "Engine imported from outside the package!"
    assert data["specialists_count"] > 0
    assert data["workflows_count"] > 0
    assert "memory/current-state.md" in data["context_files_loaded"]
    assert "memory/key-facts.md" in data["context_files_loaded"]
    assert data["lifecycle_state"] == "initialized"
    assert data["recommended_workflow"] == "analyze-requirement"

    # Clean up completely (handled inherently by pytest tmp_path, but let's assert it passes)
