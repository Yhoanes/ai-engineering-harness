from __future__ import annotations

from engine.validators import ValidationResult

# Preconditions keyed by workflow id
# These are the minimum conditions that must be true before a workflow can execute.
DEFAULT_PRECONDITIONS: dict[str, list[dict[str, str]]] = {
    "implement-task": [
        {"field": "status", "equals": "approved"},
        {"field": "approval_status", "equals": "approved"},
    ],
    "test-task": [
        {"field": "status", "equals": "in_progress"},
    ],
    "review-task": [
        {"field": "status", "equals": "in_progress"},
    ],
    "security-review": [
        {"field": "status", "equals": "in_progress"},
    ],
    "close-task": [
        {"field": "status", "equals": "in_progress"},
        {"field": "acceptance_status", "one_of": "passed,passed_with_deviation"},
    ],
    "approve-task": [
        {"field": "status", "equals": "awaiting_approval"},
    ],
}


def validate(
    task: dict,
    *,
    workflows: dict | None = None,
) -> ValidationResult:
    """Validate that workflow preconditions are met."""
    errors: list[str] = []
    warnings: list[str] = []

    workflow_id = task.get("assigned_workflow")
    if not workflow_id:
        warnings.append("No assigned_workflow — skipping precondition check")
        return ValidationResult(
            valid=True, validator_id="validate_preconditions", warnings=warnings
        )

    # Use provided workflows or fall back to defaults
    preconditions = None
    if workflows:
        workflow_def = workflows.get(workflow_id, {})
        preconditions = workflow_def.get("preconditions")

    if preconditions is None:
        preconditions = DEFAULT_PRECONDITIONS.get(workflow_id)

    if preconditions is None:
        warnings.append(f"No preconditions defined for workflow '{workflow_id}'")
        return ValidationResult(
            valid=True, validator_id="validate_preconditions", warnings=warnings
        )

    for condition in preconditions:
        field_name = condition.get("field", "")
        actual_value = task.get(field_name)

        if "equals" in condition:
            expected = condition["equals"]
            if actual_value != expected:
                errors.append(
                    f"Precondition failed: {field_name} must be '{expected}', got '{actual_value}'"
                )

        if "one_of" in condition:
            allowed_values = {v.strip() for v in condition["one_of"].split(",")}
            if actual_value not in allowed_values:
                errors.append(
                    f"Precondition failed: {field_name} must be one of "
                    f"{sorted(allowed_values)}, got '{actual_value}'"
                )

    return ValidationResult(
        valid=len(errors) == 0,
        validator_id="validate_preconditions",
        errors=errors,
        warnings=warnings,
    )
