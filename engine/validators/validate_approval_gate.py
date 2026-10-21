from __future__ import annotations

import re

from engine.validators import ValidationResult

# Simplified ISO 8601 pattern
_ISO_8601_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)$")


def validate(task: dict) -> ValidationResult:
    """Validate that a task has a structurally valid human approval."""
    errors: list[str] = []
    warnings: list[str] = []

    approval_status = task.get("approval_status")
    if approval_status != "approved":
        errors.append(f"approval_status must be 'approved', got '{approval_status}'")
        return ValidationResult(valid=False, validator_id="validate_approval_gate", errors=errors)

    approved_by = task.get("approved_by")
    if not approved_by or not isinstance(approved_by, str) or not approved_by.strip():
        errors.append("approved_by must be a non-empty string")

    approved_at = task.get("approved_at")
    if not approved_at or not isinstance(approved_at, str):
        errors.append("approved_at must be a non-empty ISO 8601 string")
    elif not _ISO_8601_PATTERN.match(approved_at):
        errors.append(f"approved_at is not valid ISO 8601: '{approved_at}'")

    # Provenance: informational, not required
    approval_source = task.get("approval_source")
    if not approval_source:
        warnings.append("approval_source is not set (recommended for audit trail)")

    return ValidationResult(
        valid=len(errors) == 0,
        validator_id="validate_approval_gate",
        errors=errors,
        warnings=warnings,
    )
