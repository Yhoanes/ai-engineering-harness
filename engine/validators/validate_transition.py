from __future__ import annotations

from engine.state_machine.transitions import (
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    is_valid_status,
)
from engine.validators import ValidationResult


def validate(from_status: str, to_status: str) -> ValidationResult:
    """Validate that a state transition is allowed."""
    errors: list[str] = []

    if not is_valid_status(from_status):
        errors.append(f"Invalid source status: '{from_status}'")
    if not is_valid_status(to_status):
        errors.append(f"Invalid target status: '{to_status}'")

    if errors:
        return ValidationResult(valid=False, validator_id="validate_transition", errors=errors)

    if from_status in TERMINAL_STATES:
        errors.append(f"Cannot transition from terminal state '{from_status}'")
        return ValidationResult(valid=False, validator_id="validate_transition", errors=errors)

    allowed = VALID_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        errors.append(
            f"Transition '{from_status}' -> '{to_status}' is not allowed. "
            f"Valid targets: {sorted(allowed)}"
        )

    return ValidationResult(
        valid=len(errors) == 0,
        validator_id="validate_transition",
        errors=errors,
    )
