from pathlib import Path

from engine.diagnostics.engine import _check_antigravity_integration


def test_antigravity_native_structure():
    root = Path(__file__).parent.parent
    agents_dir = root / ".agents"

    expected_files = [
        agents_dir / "agents.md",
        agents_dir / "rules" / "harness-governance.md",
        agents_dir / "skills" / "harness-advisor" / "SKILL.md",
        agents_dir / "workflows" / "advisor.md",
        agents_dir / "workflows" / "new-project.md",
        agents_dir / "workflows" / "evolve-harness.md"
    ]

    for f in expected_files:
        assert f.is_file(), f"{f} must exist"

def test_agents_canonical_paths():
    root = Path(__file__).parent.parent
    agents_md = root / ".agents" / "agents.md"
    content = agents_md.read_text(encoding="utf-8")
    assert "../core/specialists/harness-evolution-advisor/prompt.md" in content
    assert "../core/specialists/general-advisor/prompt.md" in content

def test_frontmatter_and_commands():
    root = Path(__file__).parent.parent

    adv = root / ".agents" / "workflows" / "advisor.md"
    assert "description:" in adv.read_text(encoding="utf-8")
    assert "trigger:" not in adv.read_text(encoding="utf-8")

    np = root / ".agents" / "workflows" / "new-project.md"
    assert "description:" in np.read_text(encoding="utf-8")
    assert "trigger:" not in np.read_text(encoding="utf-8")

    eh = root / ".agents" / "workflows" / "evolve-harness.md"
    assert "description:" in eh.read_text(encoding="utf-8")
    assert "trigger:" not in eh.read_text(encoding="utf-8")

def test_read_only_limits():
    root = Path(__file__).parent.parent
    rules_file = root / ".agents" / "rules" / "harness-governance.md"
    content = rules_file.read_text(encoding="utf-8")
    assert "read-only" in content.lower()

    agents_md = root / ".agents" / "agents.md"
    content = agents_md.read_text(encoding="utf-8")
    assert "read-only" in content.lower()

def test_diagnostics_complete(tmp_path):
    # Mock valid structure
    for rel_path in [
        ".agents/agents.md",
        ".agents/rules/harness-governance.md",
        ".agents/skills/harness-advisor/SKILL.md",
        ".agents/workflows/advisor.md",
        ".agents/workflows/new-project.md",
        ".agents/workflows/evolve-harness.md"
    ]:
        p = tmp_path / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("ok", encoding="utf-8")

    check = _check_antigravity_integration(tmp_path)
    assert check.status == "PASS"

def test_diagnostics_incomplete(tmp_path):
    (tmp_path / ".agents").mkdir()
    check = _check_antigravity_integration(tmp_path)
    assert check.status == "FAIL"
    assert "missing:" in check.message
