from engine.evolution.registry import ExtensionRegistry


def test_skill_structure_no_execution(tmp_path):
    # Ensure registry discovery does not execute scripts.
    skill_dir = tmp_path / "skills" / "mock-skill"
    skill_dir.mkdir(parents=True)

    script_dir = skill_dir / "scripts"
    script_dir.mkdir()

    evil_script = script_dir / "evil.py"
    evil_script.write_text("raise RuntimeError('Should not execute!')")

    # Discovery should succeed without raising
    registry = ExtensionRegistry(tmp_path)
    discovered = registry.discover_all()

    assert "mock-skill" in discovered
