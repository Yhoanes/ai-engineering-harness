from __future__ import annotations

import re

from engine.validators import ValidationResult

_ISO_8601_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)$")


def validate(task: dict) -> ValidationResult:
    """Validate that a task has a valid human acceptance."""
    errors: list[str] = []

    acceptance_status = task.get("acceptance_status")
    valid_statuses = {"passed", "passed_with_deviation"}

    if acceptance_status not in valid_statuses:
        errors.append(
            f"acceptance_status must be one of {sorted(valid_statuses)}, got '{acceptance_status}'"
        )
        return ValidationResult(valid=False, validator_id="validate_acceptance_gate", errors=errors)

    accepted_by = task.get("accepted_by")
    if not accepted_by or not isinstance(accepted_by, str) or not accepted_by.strip():
        errors.append("accepted_by must be a non-empty string")

    accepted_at = task.get("accepted_at")
    if not accepted_at or not isinstance(accepted_at, str):
        errors.append("accepted_at must be a non-empty ISO 8601 string")
    elif not _ISO_8601_PATTERN.match(accepted_at):
        errors.append(f"accepted_at is not valid ISO 8601: '{accepted_at}'")

    return ValidationResult(
        valid=len(errors) == 0,
        validator_id="validate_acceptance_gate",
        errors=errors,
    )
