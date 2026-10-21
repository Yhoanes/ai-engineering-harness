from engine.evolution.models import ExtensionType
from engine.evolution.registry import ExtensionRegistry, validate_extension_id


def test_validate_extension_id():
    assert validate_extension_id("valid-id") is True
    assert validate_extension_id("valid_id-123") is True
    assert validate_extension_id("123-valid") is True

    assert validate_extension_id("../evil") is False
    assert validate_extension_id("/foo") is False
    assert validate_extension_id("a/b") is False
    assert validate_extension_id("a\\b") is False
    assert validate_extension_id("with space") is False
    assert validate_extension_id("") is False


def test_registry_discovery(tmp_path):
    # Mock repo structure
    (tmp_path / "core" / "specialists" / "mock-specialist").mkdir(parents=True)
    (tmp_path / "skills" / "mock-skill").mkdir(parents=True)
    (tmp_path / "skills" / "_template").mkdir(parents=True)  # should be ignored

    registry = ExtensionRegistry(tmp_path)
    discovered = registry.discover_all()

    assert "mock-specialist" in discovered
    assert discovered["mock-specialist"]["type"] == ExtensionType.SPECIALIST

    assert "mock-skill" in discovered
    assert discovered["mock-skill"]["type"] == ExtensionType.SKILL

    assert "_template" not in discovered
