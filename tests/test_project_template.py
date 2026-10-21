import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = REPO / "templates" / "project"


def test_template_exists():
    assert TEMPLATE_DIR.exists()
    assert TEMPLATE_DIR.is_dir()


def test_template_no_binaries():
    for f in TEMPLATE_DIR.rglob("*"):
        if f.is_file():
            content = f.read_bytes()
            assert b"\x00" not in content, f"Unexpected binary in {f}"


def test_template_utf8_valid():
    for f in TEMPLATE_DIR.rglob("*"):
        if f.is_file():
            f.read_text(encoding="utf-8")  # Should not raise UnicodeDecodeError


def test_template_no_secrets():
    # Basic check for obvious secrets
    for f in TEMPLATE_DIR.rglob("*"):
        if f.is_file():
            content = f.read_text(encoding="utf-8")
            assert "AKIA" not in content
            assert "PRIVATE KEY" not in content


def test_template_no_machine_paths():
    for f in TEMPLATE_DIR.rglob("*"):
        if f.is_file():
            content = f.read_text(encoding="utf-8")
            assert "C:\\" + "Users\\" not in content
            assert "/" + "home/" not in content


def test_template_no_caches():
    for item in TEMPLATE_DIR.rglob("*"):
        assert item.name not in ["__pycache__", ".pytest_cache", ".ruff_cache"]


def test_template_valid_placeholders():
    allowed_placeholders = {
        "PROJECT_KEY",
        "PROJECT_NAME",
        "INITIAL_DESCRIPTION",
        "CONFIRMED_FACTS",
        "PRELIMINARY_DECISIONS",
    }
    found_placeholders = set()
    for f in TEMPLATE_DIR.rglob("*"):
        if f.is_file():
            content = f.read_text(encoding="utf-8")
            matches = set(re.findall(r"\{\{([A-Z_]+)\}\}", content))
            found_placeholders.update(matches)
            for m in matches:
                assert m in allowed_placeholders, f"Invalid placeholder {m} found in {f}"


def test_template_structure():
    expected_files = [
        "README.md",
        "memory/current-state.md",
        "memory/key-facts.md",
        "context/product-definition.md",
        "context/business-rules.md",
        "context/glossary.md",
        "requirements/README.md",
        "architecture/README.md",
        "adrs/README.md",
        "tasks/README.md",
        "evidence/README.md",
        "source/README.md",
    ]
    for rel_path in expected_files:
        assert (TEMPLATE_DIR / rel_path).exists()
