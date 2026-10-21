from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator

SCHEMA_DIR = Path(__file__).parent.parent / "core" / "schemas"

SCHEMA_FILES = [
    "task-contract.schema.yaml",
    "task-contract-light.schema.yaml",
    "approval.schema.yaml",
    "acceptance.schema.yaml",
    "deviation.schema.yaml",
    "specialist.schema.yaml",
    "workflow.schema.yaml",
    "state-machine.yaml",
]


@pytest.mark.parametrize("schema_file", SCHEMA_FILES)
def test_schema_loads(schema_file: str) -> None:
    """Each schema file should load as valid YAML."""
    path = SCHEMA_DIR / schema_file
    assert path.exists(), f"Schema file not found: {path}"
    with path.open() as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), f"Schema {schema_file} should be a dict"


def test_state_machine_has_required_fields() -> None:
    """State machine schema must define status_values, terminal_states, transitions."""
    path = SCHEMA_DIR / "state-machine.yaml"
    with path.open() as f:
        sm = yaml.safe_load(f)
    assert "status_values" in sm
    assert "terminal_states" in sm
    assert "transitions" in sm
    assert "rejected" in sm["terminal_states"]


def test_task_contract_schema_has_required_properties() -> None:
    """Task contract schema must define required fields."""
    path = SCHEMA_DIR / "task-contract.schema.yaml"
    with path.open() as f:
        schema = yaml.safe_load(f)
    required = schema.get("required", [])
    assert "task_id" in required
    assert "status" in required
    assert "approval_status" in required
    assert "acceptance_status" in required


# ─── Specialist Schema Tests (AC-03, AC-04, AC-07, AC-08, AC-09, AC-10) ───


def _load_specialist_schema() -> dict:
    path = SCHEMA_DIR / "specialist.schema.yaml"
    with path.open() as f:
        return yaml.safe_load(f)


def _valid_specialist() -> dict:
    """Return a minimal valid specialist definition."""
    return {
        "id": "test-specialist",
        "display_name": "Test Specialist",
        "description": "A test specialist for validation.",
        "category": "implementation",
        "purpose": "Validate the specialist schema.",
        "capabilities": ["testing"],
        "limitations": ["cannot deploy"],
        "authority_profile": "backend-engineer",
        "task_capabilities": {
            "propose_task": True,
            "create_task": False,
            "approve_task": False,
            "accept_task": False,
            "close_task": False,
        },
        "context_requirements": ["codebase"],
        "output_contract": {
            "format": "markdown",
            "sections": ["summary", "changes"],
        },
        "escalation_rules": ["Escalate to tech-lead on ambiguity"],
    }


def test_specialist_schema_valid_complete() -> None:
    """A complete specialist definition must validate successfully."""
    from jsonschema import Draft7Validator

    schema = _load_specialist_schema()
    specialist = _valid_specialist()
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(specialist))
    assert len(errors) == 0, f"Valid specialist should pass: {[e.message for e in errors]}"


@pytest.mark.parametrize(
    "missing_field",
    [
        "id",
        "display_name",
        "description",
        "category",
        "purpose",
        "capabilities",
        "limitations",
        "authority_profile",
        "task_capabilities",
        "context_requirements",
        "output_contract",
        "escalation_rules",
    ],
)
def test_specialist_schema_missing_required_field(missing_field: str) -> None:
    """Removing any required field must cause validation failure."""
    from jsonschema import Draft7Validator

    schema = _load_specialist_schema()
    specialist = _valid_specialist()
    del specialist[missing_field]
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(specialist))
    assert len(errors) > 0, f"Missing '{missing_field}' should fail validation"


@pytest.mark.parametrize(
    "missing_cap",
    ["propose_task", "create_task", "approve_task", "accept_task", "close_task"],
)
def test_specialist_schema_incomplete_task_capabilities(missing_cap: str) -> None:
    """task_capabilities missing any required boolean must fail."""
    from jsonschema import Draft7Validator

    schema = _load_specialist_schema()
    specialist = _valid_specialist()
    del specialist["task_capabilities"][missing_cap]
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(specialist))
    assert len(errors) > 0, f"Missing task_capabilities.{missing_cap} should fail"


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("id", 123),  # should be string
        ("display_name", ""),  # minLength: 1
        ("category", "nonexistent"),  # not in enum
        ("capabilities", "not-a-list"),  # should be array
        ("limitations", []),  # minItems: 1
        ("authority_profile", ""),  # minLength: 1
        ("task_capabilities", "not-an-object"),  # should be object
        ("escalation_rules", []),  # minItems: 1
    ],
)
def test_specialist_schema_invalid_types(field: str, bad_value) -> None:
    """Invalid types or values in specialist fields must fail validation."""
    from jsonschema import Draft7Validator

    schema = _load_specialist_schema()
    specialist = _valid_specialist()
    specialist[field] = bad_value
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(specialist))
    assert len(errors) > 0, f"Invalid {field}={bad_value!r} should fail"


def test_specialist_schema_task_capabilities_no_extra_fields() -> None:
    """task_capabilities must not accept additional properties."""
    from jsonschema import Draft7Validator

    schema = _load_specialist_schema()
    specialist = _valid_specialist()
    specialist["task_capabilities"]["extra_field"] = True
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(specialist))
    assert len(errors) > 0, "Extra fields in task_capabilities should fail"


def test_specialist_schema_requires_all_fields() -> None:
    """Verify the schema lists all 12 required fields."""
    schema = _load_specialist_schema()
    required = schema.get("required", [])
    expected = {
        "id",
        "display_name",
        "description",
        "category",
        "purpose",
        "capabilities",
        "limitations",
        "authority_profile",
        "task_capabilities",
        "context_requirements",
        "output_contract",
        "escalation_rules",
    }
    assert set(required) == expected, f"Required fields mismatch: {set(required)} != {expected}"


# --- Workflow Schema Tests ---


def _load_workflow_schema() -> dict:
    path = SCHEMA_DIR / "workflow.schema.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _valid_workflow() -> dict:
    return {
        "id": "test-workflow",
        "display_name": "Test Workflow",
        "description": "A workflow for testing schema validation.",
        "purpose": "Verify schema strictness",
        "allowed_specialists": ["harness-maintainer"],
        "entry_conditions": [{"field": "status", "operator": "equals", "value": "in_progress"}],
        "steps": [
            {
                "id": "step-1",
                "description": "First step",
                "actor": "harness-maintainer",
                "action": "validate",
                "required": True,
                "on_failure": "abort",
            }
        ],
        "required_validators": ["V1"],
        "evidence_requirements": [
            {"id": "ev-1", "description": "Test evidence", "type": "status", "required": True}
        ],
        "exit_conditions": [{"field": "status", "operator": "equals", "value": "completed"}],
        "next_workflows": [{"id": "close-task", "condition_summary": "when done"}],
        "forbidden_actions": ["delete_repo"],
    }


def test_workflow_schema_valid_complete() -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(workflow))
    assert not errors, f"Valid workflow should pass: {[e.message for e in errors]}"


@pytest.mark.parametrize(
    "missing_field",
    [
        "id",
        "display_name",
        "description",
        "purpose",
        "allowed_specialists",
        "entry_conditions",
        "steps",
        "required_validators",
        "evidence_requirements",
        "exit_conditions",
        "next_workflows",
        "forbidden_actions",
    ],
)
def test_workflow_schema_missing_required(missing_field: str) -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    del workflow[missing_field]
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(workflow))
    assert len(errors) > 0, f"Workflow missing '{missing_field}' should fail validation"


def test_workflow_schema_unknown_property() -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    workflow["unknown_prop"] = "foo"
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(workflow))
    assert len(errors) > 0, (
        "Workflow with unknown property should fail (additionalProperties: false)"
    )


@pytest.mark.parametrize("valid_id", ["discuss", "analyze-requirement", "security-review"])
def test_workflow_schema_valid_ids(valid_id: str) -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    workflow["id"] = valid_id
    validator = Draft7Validator(schema)
    assert not list(validator.iter_errors(workflow))


@pytest.mark.parametrize("invalid_id", ["Discuss", "analyze_req", "analyze requirement", ""])
def test_workflow_schema_invalid_ids(invalid_id: str) -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    workflow["id"] = invalid_id
    validator = Draft7Validator(schema)
    assert list(validator.iter_errors(workflow))


@pytest.mark.parametrize(
    "array_field", ["allowed_specialists", "required_validators", "forbidden_actions"]
)
def test_workflow_schema_duplicate_arrays(array_field: str) -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    workflow[array_field] = ["dup", "dup"]
    validator = Draft7Validator(schema)
    assert list(validator.iter_errors(workflow))


def test_workflow_schema_invalid_types() -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    workflow["steps"] = "not an array"
    validator = Draft7Validator(schema)
    assert list(validator.iter_errors(workflow))


def test_workflow_schema_steps_empty() -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    workflow["steps"] = []
    validator = Draft7Validator(schema)
    assert list(validator.iter_errors(workflow))


def test_workflow_schema_malformed_step() -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    del workflow["steps"][0]["action"]
    validator = Draft7Validator(schema)
    assert list(validator.iter_errors(workflow))


def test_workflow_schema_extra_property_in_step() -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    workflow["steps"][0]["extra"] = "value"
    validator = Draft7Validator(schema)
    assert list(validator.iter_errors(workflow))


def test_workflow_schema_malformed_entry_condition() -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    del workflow["entry_conditions"][0]["operator"]
    validator = Draft7Validator(schema)
    assert list(validator.iter_errors(workflow))


def test_workflow_schema_malformed_exit_condition() -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    workflow["exit_conditions"][0]["operator"] = "invalid_operator"
    validator = Draft7Validator(schema)
    assert list(validator.iter_errors(workflow))


def test_workflow_schema_malformed_evidence_requirement() -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    del workflow["evidence_requirements"][0]["required"]
    validator = Draft7Validator(schema)
    assert list(validator.iter_errors(workflow))


def test_workflow_schema_malformed_next_workflow() -> None:
    schema = _load_workflow_schema()
    workflow = _valid_workflow()
    workflow["next_workflows"][0]["extra"] = "foo"
    validator = Draft7Validator(schema)
    assert list(validator.iter_errors(workflow))
