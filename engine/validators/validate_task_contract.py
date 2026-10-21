from __future__ import annotations

from pathlib import Path

import yaml
from jsonschema import Draft7Validator

from engine.validators import ValidationResult

SCHEMA_DIR = Path(__file__).parent.parent.parent / "core" / "schemas"


def _load_schema(task_type: str) -> dict:
    """Load the appropriate schema based on task type."""
    if task_type == "light":
        schema_file = SCHEMA_DIR / "task-contract-light.schema.yaml"
    else:
        schema_file = SCHEMA_DIR / "task-contract.schema.yaml"
    with schema_file.open() as f:
        return yaml.safe_load(f)


def validate(task: dict) -> ValidationResult:
    """Validate a task contract against its JSON schema."""
    errors: list[str] = []
    warnings: list[str] = []

    task_type = task.get("task_type", "standard")

    try:
        schema = _load_schema(task_type)
    except FileNotFoundError as e:
        return ValidationResult(
            valid=False,
            validator_id="validate_task_contract",
            errors=[f"Schema file not found: {e}"],
        )

    validator = Draft7Validator(schema)
    for error in sorted(validator.iter_errors(task), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.path) or "(root)"
        errors.append(f"{path}: {error.message}")

    # Additional structural checks beyond JSON schema
    _check_approval_consistency(task, errors)
    _check_acceptance_consistency(task, errors)
    _check_specialist_assignment(task, errors, warnings)

    return ValidationResult(
        valid=len(errors) == 0,
        validator_id="validate_task_contract",
        errors=errors,
        warnings=warnings,
    )


def _check_approval_consistency(task: dict, errors: list[str]) -> None:
    """Check that approval fields are consistent."""
    status = task.get("approval_status")
    if status == "approved":
        if not task.get("approved_by"):
            errors.append("approval_status is 'approved' but approved_by is missing")
        if not task.get("approved_at"):
            errors.append("approval_status is 'approved' but approved_at is missing")
    elif status == "pending":
        if task.get("approved_by"):
            errors.append("approval_status is 'pending' but approved_by is set")


def _check_acceptance_consistency(task: dict, errors: list[str]) -> None:
    """Check that acceptance fields are consistent."""
    status = task.get("acceptance_status")
    if status in ("passed", "passed_with_deviation"):
        if not task.get("accepted_by"):
            errors.append(f"acceptance_status is '{status}' but accepted_by is missing")
        if not task.get("accepted_at"):
            errors.append(f"acceptance_status is '{status}' but accepted_at is missing")


def _check_specialist_assignment(task: dict, errors: list[str], warnings: list[str]) -> None:
    """Check that approved tasks have at least one assigned specialist."""
    status = task.get("status")
    approval_status = task.get("approval_status")
    assigned = task.get("assigned_specialists", [])

    is_approved_or_active = (
        status not in ("draft", "awaiting_approval")
        or approval_status == "approved"
    )
    is_missing_assignment = not assigned or len(assigned) == 0
    if is_approved_or_active and is_missing_assignment:
        if status == "completed":
            warnings.append(
                "Task was completed without assigned_specialists (governance deviation)."
            )
        else:
            errors.append(
                "assigned_specialists cannot be empty for an approved or active task."
            )

def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Task Contract Validator CLI")
    parser.add_argument("task_contract", help="Path to the task contract YAML file")

    args = parser.parse_args(argv)

    contract_path = Path(args.task_contract)

    if not contract_path.is_file():
        print(f"INPUT ERROR: File not found: {contract_path}")
        return 2

    try:
        with contract_path.open(encoding="utf-8") as f:
            task = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"INPUT ERROR: Malformed YAML: {e}")
        return 2
    except OSError as e:
        print(f"INPUT ERROR: Could not read file: {e}")
        return 2

    if not isinstance(task, dict):
        print(f"INPUT ERROR: Task contract must be a YAML dictionary, got {type(task).__name__}")
        return 2

    result = validate(task)

    if result.valid:
        print("Task Contract validation: PASS")
        return 0
    else:
        print("Task Contract validation: FAIL")
        print("Errors:")
        for error in result.errors:
            print(f"- {error}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
