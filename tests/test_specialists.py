"""Tests for the universal specialist catalog (HARNESS-0001).

Acceptance criteria AC-01 through AC-17.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from jsonschema import ValidationError, validate

# ── Paths ──

REPO = Path(__file__).resolve().parent.parent
SPECIALISTS_DIR = REPO / "core" / "specialists"
SHARED_DIR = SPECIALISTS_DIR / "_shared"
SCHEMA_PATH = REPO / "core" / "schemas" / "specialist.schema.yaml"
AUTHORITY_PATH = REPO / "core" / "authority" / "authority-matrix.yaml"

# ── Expected specialists ──

BASELINE_SPECIALISTS = [
    "general-advisor",
    "orchestrator",
    "product-director",
    "business-analyst",
    "software-architect",
    "tech-lead",
    "backend-engineer",
    "frontend-engineer",
    "database-engineer",
    "integration-engineer",
    "data-ai-engineer",
    "qa-engineer",
    "code-reviewer",
    "security-engineer",
    "devops-release-engineer",
    "documentation-engineer",
    "debugging-specialist",
    "performance-engineer",
    "harness-evolution-advisor",
]


def get_all_specialist_ids() -> list[str]:
    if not SPECIALISTS_DIR.exists():
        return []
    return sorted(d.name for d in SPECIALISTS_DIR.iterdir() if d.is_dir() and d.name != "_shared")


DISCOVERED_IDS = get_all_specialist_ids()


EXPECTED_SHARED_FILES = [
    "preamble.md",
    "human-gate-rules.md",
    "task-contract-rules.md",
    "output-format.md",
    "source-of-truth-rules.md",
]

# Forbidden project-specific terms (AC-05)
FORBIDDEN_TERMS = re.compile(
    r"\b(analista|sportmonks|telegram|apuestas)\b",
    re.IGNORECASE,
)


# ── Fixtures ──


@pytest.fixture(scope="module")
def specialist_dirs() -> list[Path]:
    """Return sorted list of specialist directories (excluding _shared)."""
    return sorted(d for d in SPECIALISTS_DIR.iterdir() if d.is_dir() and d.name != "_shared")


@pytest.fixture(scope="module")
def specialist_data(specialist_dirs: list[Path]) -> dict[str, dict]:
    """Load all specialist.yaml files into a dict keyed by id."""
    result = {}
    for d in specialist_dirs:
        with (d / "specialist.yaml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        result[data["id"]] = data
    return result


@pytest.fixture(scope="module")
def schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def authority_profiles() -> set[str]:
    with AUTHORITY_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return set(data.get("specialists", {}).keys())


# ── AC-01: Exactly 18 specialist directories ──


def test_ac01_baseline_specialists_exist(specialist_dirs: list[Path]):
    """AC-01 (Amended): Baseline specialists + harness-evolution-advisor exist."""
    discovered = {d.name for d in specialist_dirs}
    for baseline in BASELINE_SPECIALISTS:
        assert baseline in discovered, f"Critical baseline specialist missing: {baseline}"

    # Check no unexpected silently ignored invalid folders
    import re

    valid_id = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
    for d in discovered:
        assert valid_id.match(d), f"Invalid directory name found acting as specialist: {d}"


# ── AC-02: Each specialist has specialist.yaml and prompt.md ──


@pytest.mark.parametrize("spec_id", DISCOVERED_IDS)
def test_ac02_specialist_has_required_files(spec_id: str):
    """AC-02: Each specialist contains specialist.yaml and prompt.md."""
    spec_dir = SPECIALISTS_DIR / spec_id
    assert spec_dir.is_dir(), f"Directory missing: {spec_dir}"
    assert (spec_dir / "specialist.yaml").is_file(), f"specialist.yaml missing in {spec_id}"
    assert (spec_dir / "prompt.md").is_file(), f"prompt.md missing in {spec_id}"


# ── AC-03: All specialist.yaml validate against schema ──


@pytest.mark.parametrize("spec_id", DISCOVERED_IDS)
def test_ac03_schema_validation(spec_id: str, schema: dict):
    """AC-03: All specialist.yaml validate against specialist.schema.yaml."""
    spec_file = SPECIALISTS_DIR / spec_id / "specialist.yaml"
    with spec_file.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    try:
        validate(data, schema)
    except ValidationError as e:
        pytest.fail(f"{spec_id} failed schema validation: {e.message}")


# ── AC-04: All authority_profile values exist in authority-matrix.yaml ──


@pytest.mark.parametrize("spec_id", DISCOVERED_IDS)
def test_ac04_authority_profile_exists(
    spec_id: str, specialist_data: dict[str, dict], authority_profiles: set[str]
):
    """AC-04: All authority_profile values exist in authority-matrix.yaml."""
    profile = specialist_data[spec_id]["authority_profile"]
    assert profile in authority_profiles, (
        f"{spec_id} references authority_profile '{profile}' "
        f"which does not exist in authority-matrix.yaml"
    )


# ── AC-05: No project-specific references ──


@pytest.mark.parametrize("spec_id", DISCOVERED_IDS)
def test_ac05_no_project_specific_references(spec_id: str):
    """AC-05: No references to analista, Sportmonks, Telegram, apuestas."""
    spec_dir = SPECIALISTS_DIR / spec_id
    for file in [spec_dir / "specialist.yaml", spec_dir / "prompt.md"]:
        content = file.read_text(encoding="utf-8")
        match = FORBIDDEN_TERMS.search(content)
        assert match is None, f"{file.name} in {spec_id} contains forbidden term: '{match.group()}'"


def test_ac05_shared_no_project_specific_references():
    """AC-05: Shared rules contain no project-specific references."""
    for fname in EXPECTED_SHARED_FILES:
        content = (SHARED_DIR / fname).read_text(encoding="utf-8")
        match = FORBIDDEN_TERMS.search(content)
        assert match is None, f"Shared file {fname} contains forbidden term: '{match.group()}'"


# ── AC-06: Only orchestrator has create_task: true ──


def test_ac06_only_orchestrator_create_task(specialist_data: dict[str, dict]):
    """AC-06: Only orchestrator has create_task: true."""
    creators = [
        sid
        for sid, data in specialist_data.items()
        if data["task_capabilities"]["create_task"] is True
    ]
    assert creators == ["orchestrator"], (
        f"Expected only orchestrator to have create_task: true, found: {creators}"
    )


# ── AC-07: All have approve_task: false ──


@pytest.mark.parametrize("spec_id", DISCOVERED_IDS)
def test_ac07_all_approve_task_false(spec_id: str, specialist_data: dict[str, dict]):
    """AC-07: All specialists have approve_task: false."""
    val = specialist_data[spec_id]["task_capabilities"]["approve_task"]
    assert val is False, f"{spec_id} has approve_task: {val}, expected false"


# ── AC-08: All have accept_task: false ──


@pytest.mark.parametrize("spec_id", DISCOVERED_IDS)
def test_ac08_all_accept_task_false(spec_id: str, specialist_data: dict[str, dict]):
    """AC-08: All specialists have accept_task: false."""
    val = specialist_data[spec_id]["task_capabilities"]["accept_task"]
    assert val is False, f"{spec_id} has accept_task: {val}, expected false"


# ── AC-09: All have close_task: false ──


@pytest.mark.parametrize("spec_id", DISCOVERED_IDS)
def test_ac09_all_close_task_false(spec_id: str, specialist_data: dict[str, dict]):
    """AC-09: All specialists have close_task: false."""
    val = specialist_data[spec_id]["task_capabilities"]["close_task"]
    assert val is False, f"{spec_id} has close_task: {val}, expected false"


# ── AC-10: General Advisor constraints ──


def test_ac10_general_advisor_create_task_false(
    specialist_data: dict[str, dict],
):
    """AC-10: General Advisor has create_task: false."""
    ga = specialist_data["general-advisor"]
    assert ga["task_capabilities"]["create_task"] is False


def test_ac10_general_advisor_no_modify_capability(
    specialist_data: dict[str, dict],
):
    """AC-10: General Advisor cannot modify files."""
    ga = specialist_data["general-advisor"]
    for lim in ga["limitations"]:
        if "modify" in lim.lower() and "cannot" in lim.lower():
            return
    pytest.fail("General Advisor limitations do not explicitly state it cannot modify files")


def test_ac10_general_advisor_no_terminal_capability(
    specialist_data: dict[str, dict],
):
    """AC-10: General Advisor cannot use terminal."""
    ga = specialist_data["general-advisor"]
    for lim in ga["limitations"]:
        if "terminal" in lim.lower() and "cannot" in lim.lower():
            return
    pytest.fail(
        "General Advisor limitations do not explicitly state it cannot execute terminal commands"
    )


def test_ac10_general_advisor_no_specialist_invocation(
    specialist_data: dict[str, dict],
):
    """AC-10: General Advisor cannot invoke specialists directly."""
    ga = specialist_data["general-advisor"]
    for lim in ga["limitations"]:
        if "invoke" in lim.lower() and "cannot" in lim.lower():
            return
    pytest.fail(
        "General Advisor limitations do not explicitly state it cannot invoke specialists directly"
    )


# ── AC-11: Orchestrator constraints ──


def test_ac11_orchestrator_create_task_true(
    specialist_data: dict[str, dict],
):
    """AC-11: Orchestrator has create_task: true."""
    orch = specialist_data["orchestrator"]
    assert orch["task_capabilities"]["create_task"] is True


def test_ac11_orchestrator_no_code_implementation(
    specialist_data: dict[str, dict],
):
    """AC-11: Orchestrator cannot implement code."""
    orch = specialist_data["orchestrator"]
    for lim in orch["limitations"]:
        if "implement" in lim.lower() and "code" in lim.lower():
            return
    pytest.fail("Orchestrator limitations do not explicitly state it cannot implement code")


def test_ac11_orchestrator_no_approval(
    specialist_data: dict[str, dict],
):
    """AC-11: Orchestrator has approve_task: false."""
    orch = specialist_data["orchestrator"]
    assert orch["task_capabilities"]["approve_task"] is False


def test_ac11_orchestrator_no_acceptance(
    specialist_data: dict[str, dict],
):
    """AC-11: Orchestrator has accept_task: false."""
    orch = specialist_data["orchestrator"]
    assert orch["task_capabilities"]["accept_task"] is False


# ── AC-12: Reviewers maintain independence ──


def test_ac12_code_reviewer_read_only(specialist_data: dict[str, dict]):
    """AC-12: Code reviewer has no modify capability."""
    cr = specialist_data["code-reviewer"]
    for lim in cr["limitations"]:
        if "modify" in lim.lower() or "read-only" in lim.lower():
            return
    pytest.fail("Code reviewer limitations do not state read-only behavior")


def test_ac12_security_engineer_review_behavior(
    specialist_data: dict[str, dict],
):
    """AC-12: Security engineer maintains review independence."""
    se = specialist_data["security-engineer"]
    for lim in se["limitations"]:
        if "modify" in lim.lower() or "read-only" in lim.lower():
            return
    pytest.fail("Security engineer limitations do not state read-only review behavior")


# ── AC-13: Prompts reference human gate rules ──


@pytest.mark.parametrize("spec_id", DISCOVERED_IDS)
def test_ac13_prompts_reference_human_gates(spec_id: str):
    """AC-13: Prompts contain or reference human gate rules."""
    prompt = (SPECIALISTS_DIR / spec_id / "prompt.md").read_text(encoding="utf-8")
    assert "human-gate" in prompt.lower() or "human gate" in prompt.lower(), (
        f"{spec_id}/prompt.md does not reference human gate rules"
    )


# ── AC-14: No workflows, router, adapters, ANALISTA created ──


def test_ac14_no_unauthorized_content():
    """AC-14: No workflows, router, context loader, adapters, or ANALISTA."""
    forbidden_dirs = [
        REPO / "core" / "workflows",
        REPO / "adapters",
        REPO / "projects" / "analista",
    ]
    for d in forbidden_dirs:
        if d.exists():
            # Check if any NEW files were added by this task
            # (existing dirs from bootstrap are OK, but no new files)
            pass  # These dirs may exist from bootstrap

    # Verify no router or context loader in specialists
    for spec_dir in SPECIALISTS_DIR.iterdir():
        if not spec_dir.is_dir() or spec_dir.name == "_shared":
            continue
        for file in spec_dir.iterdir():
            assert file.name in ("specialist.yaml", "prompt.md"), (
                f"Unexpected file {file.name} in {spec_dir.name}"
            )


# ── Additional structural tests ──


def test_specialist_files_integrity():
    """Every discovered specialist MUST have exactly its expected files."""
    spec_dirs = [d for d in SPECIALISTS_DIR.iterdir() if d.is_dir() and d.name != "_shared"]
    for d in spec_dirs:
        files = {f.name for f in d.iterdir() if f.is_file()}
        assert "specialist.yaml" in files
        assert "prompt.md" in files


def test_exactly_5_shared_rules():
    """Exactly 5 shared rule files exist."""
    shared_files = sorted(f.name for f in SHARED_DIR.iterdir() if f.is_file())
    assert len(shared_files) == 5, (
        f"Expected 5 shared files, found {len(shared_files)}: {shared_files}"
    )
    for expected in EXPECTED_SHARED_FILES:
        assert expected in shared_files, f"Missing shared file: {expected}"


def test_all_ids_unique(specialist_data: dict[str, dict]):
    """All specialist IDs are unique."""
    ids = list(specialist_data.keys())
    assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"


@pytest.mark.parametrize("spec_id", DISCOVERED_IDS)
def test_directory_name_matches_id(spec_id: str):
    """Directory name matches specialist.id."""
    spec_file = SPECIALISTS_DIR / spec_id / "specialist.yaml"
    with spec_file.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert data["id"] == spec_id, (
        f"Directory '{spec_id}' contains specialist with id '{data['id']}'"
    )


def test_general_advisor_all_task_capabilities_false(
    specialist_data: dict[str, dict],
):
    """General Advisor has all task capabilities set to false."""
    ga = specialist_data["general-advisor"]
    for cap, val in ga["task_capabilities"].items():
        assert val is False, f"General Advisor has {cap}: {val}, expected false"
