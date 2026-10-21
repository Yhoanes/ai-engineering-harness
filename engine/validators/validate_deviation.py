from __future__ import annotations

import re

from engine.validators import ValidationResult

_ISO_8601_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)$")


def validate(task: dict) -> ValidationResult:
    """Validate the deviation block when status is completed_with_deviation."""
    errors: list[str] = []

    status = task.get("status")
    acceptance_status = task.get("acceptance_status")
    deviation = task.get("deviation", {})

    # Only enforce if task is completing with deviation
    if status != "completed_with_deviation" and acceptance_status != "passed_with_deviation":
        return ValidationResult(
            valid=True,
            validator_id="validate_deviation",
            warnings=["Deviation validation not required for this status"],
        )

    if not deviation.get("documented"):
        errors.append("deviation.documented must be true")

    description = deviation.get("description")
    if not description or not isinstance(description, str) or not description.strip():
        errors.append("deviation.description must be a non-empty string")

    impact = deviation.get("impact")
    if not impact or not isinstance(impact, str) or not impact.strip():
        errors.append("deviation.impact must be a non-empty string")

    accepted_by = deviation.get("accepted_by")
    if not accepted_by or not isinstance(accepted_by, str) or not accepted_by.strip():
        errors.append("deviation.accepted_by must be a non-empty string")

    accepted_at = deviation.get("accepted_at")
    if not accepted_at or not isinstance(accepted_at, str):
        errors.append("deviation.accepted_at must be a non-empty ISO 8601 string")
    elif not _ISO_8601_PATTERN.match(accepted_at):
        errors.append(f"deviation.accepted_at is not valid ISO 8601: '{accepted_at}'")

    # Cross-check: deviation.accepted_by should match task.accepted_by
    task_accepted_by = task.get("accepted_by")
    if task_accepted_by and accepted_by and task_accepted_by != accepted_by:
        errors.append(
            f"deviation.accepted_by ('{accepted_by}') does not match "
            f"task.accepted_by ('{task_accepted_by}')"
        )

    return ValidationResult(
        valid=len(errors) == 0,
        validator_id="validate_deviation",
        errors=errors,
    )
