from __future__ import annotations

from engine.execution.models import AccessMode
from engine.governance.authority import get_execution_authority, path_allows, scope_allows
from engine.validators import ValidationResult
from engine.validators.scope import normalize_access_scope


def validate(
    task: dict,
    *,
    authority_matrix: dict | None = None,
) -> ValidationResult:
    """Pre-check: validate that planned_paths are within authority scope."""
    errors: list[str] = []
    warnings: list[str] = []

    scope = task.get("scope", {})
    raw_modify = scope.get("planned_paths", {}).get("modify", [])

    try:
        scoped_modify = normalize_access_scope(raw_modify)
    except Exception as e:
        return ValidationResult(
            valid=False,
            validator_id="validate_allowed_paths_pre",
            errors=[f"Invalid modify scope: {e}"],
        )

    if scoped_modify.mode == AccessMode.DENY_ALL:
        errors.append("scope.planned_paths.modify resolves to DENY_ALL - no paths defined")
        return ValidationResult(
            valid=False, validator_id="validate_allowed_paths_pre", errors=errors
        )

    if authority_matrix is None:
        if scoped_modify.mode == AccessMode.UNRESTRICTED:
            errors.append(
                "Task requires UNRESTRICTED modify access, but no Authority Matrix "
                "was provided to grant it."
            )
            return ValidationResult(
                valid=False, validator_id="validate_allowed_paths_pre", errors=errors
            )
        warnings.append("No authority_matrix provided - skipping authority check")
        return ValidationResult(
            valid=True,
            validator_id="validate_allowed_paths_pre",
            warnings=warnings,
        )

    specialists = task.get("assigned_specialists", [])
    for specialist_id in specialists:
        try:
            exec_auth = get_execution_authority(authority_matrix, specialist_id)
        except ValueError as e:
            errors.append(str(e))
            continue

        matrix_modify = exec_auth.modify_paths

        if matrix_modify.mode == AccessMode.DENY_ALL:
            errors.append(
                f"Specialist '{specialist_id}' has DENY_ALL modify permissions "
                f"but task assigns modification paths"
            )
            continue

        if not scope_allows(matrix_modify, scoped_modify, path_allows):
            if scoped_modify.mode == AccessMode.UNRESTRICTED:
                errors.append(
                    f"Task requires UNRESTRICTED modify access, but "
                    f"specialist '{specialist_id}' only has ALLOW_LIST."
                )
            else:
                errors.append(
                    f"Planned paths exceed authority of "
                    f"specialist '{specialist_id}' (allowed: {list(matrix_modify.values)})"
                )

    return ValidationResult(
        valid=len(errors) == 0,
        validator_id="validate_allowed_paths_pre",
        errors=errors,
        warnings=warnings,
    )
