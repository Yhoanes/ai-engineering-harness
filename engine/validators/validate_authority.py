from __future__ import annotations

from engine.execution.models import AccessMode
from engine.governance.authority import get_execution_authority, network_allows
from engine.validators import ValidationResult
from engine.validators.scope import normalize_access_scope


def validate(
    specialist_id: str,
    task: dict,
    *,
    authority_matrix: dict | None = None,
) -> ValidationResult:
    """Validate that a specialist's actions don't exceed authority matrix permissions."""
    errors: list[str] = []
    warnings: list[str] = []

    if not specialist_id:
        errors.append("specialist_id is empty")
        return ValidationResult(valid=False, validator_id="validate_authority", errors=errors)

    raw_modify = task.get("scope", {}).get("planned_paths", {}).get("modify", [])
    try:
        scoped_modify = normalize_access_scope(raw_modify)
    except Exception as e:
        errors.append(f"Invalid modify scope: {e}")
        return ValidationResult(valid=False, validator_id="validate_authority", errors=errors)

    if authority_matrix is None:
        warnings.append("No authority_matrix provided - cannot validate permissions")
        if scoped_modify.mode == AccessMode.UNRESTRICTED:
            errors.append(
                "Task requires explicit UNRESTRICTED modify authority, "
                "but no Authority Matrix was provided."
            )
            return ValidationResult(
                valid=False,
                validator_id="validate_authority",
                errors=errors,
                warnings=warnings,
            )
        return ValidationResult(valid=True, validator_id="validate_authority", warnings=warnings)

    specialists = authority_matrix.get("specialists", {})
    spec_auth = specialists.get(specialist_id)

    if spec_auth is None:
        errors.append(f"Specialist '{specialist_id}' not found in authority matrix")
        return ValidationResult(valid=False, validator_id="validate_authority", errors=errors)

    forbidden = spec_auth.get("forbidden", [])

    for action in ["approve_task", "accept_task", "close_task"]:
        if action not in forbidden:
            errors.append(f"Specialist '{specialist_id}' must have '{action}' in forbidden list")

    try:
        exec_auth = get_execution_authority(authority_matrix, specialist_id)
    except ValueError as e:
        errors.append(str(e))
        return ValidationResult(
            valid=False,
            validator_id="validate_authority",
            errors=errors,
            warnings=warnings,
        )

    if exec_auth.modify_paths.mode == AccessMode.DENY_ALL:
        if scoped_modify.mode != AccessMode.DENY_ALL:
            errors.append(
                f"Specialist '{specialist_id}' has DENY_ALL modify permissions "
                f"but task requires modifications"
            )
    elif (
        exec_auth.modify_paths.mode == AccessMode.ALLOW_LIST
        and scoped_modify.mode == AccessMode.UNRESTRICTED
    ):
        errors.append(
            "Task requires explicit UNRESTRICTED modify authority, "
            "but Authority Matrix only grants ALLOW_LIST."
        )

    requested_network = (
        task.get("scope", {}).get("allowed_actions", {}).get("network_allowed", False)
    )

    if not network_allows(exec_auth.network_allowed, requested_network):
        errors.append(
            f"Task requires network access, but Authority Matrix "
            f"does not grant network_allowed for specialist '{specialist_id}'."
        )
    return ValidationResult(
        valid=len(errors) == 0,
        validator_id="validate_authority",
        errors=errors,
        warnings=warnings,
    )
