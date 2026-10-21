from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

import yaml
from jsonschema import ValidationError, validate

from engine.execution.models import AccessMode, ScopedAccess
from engine.validators.scope import normalize_access_scope


def get_schema_path() -> Path:
    return Path(__file__).parent.parent.parent / "core" / "schemas" / "authority-matrix.schema.yaml"


def validate_authority_matrix_data(matrix_data: dict) -> None:
    schema_path = get_schema_path()
    if not schema_path.is_file():
        raise FileNotFoundError(f"Authority Matrix Schema not found at {schema_path}")
    with open(schema_path, encoding="utf-8") as f:
        schema_data = yaml.safe_load(f)
    try:
        validate(instance=matrix_data, schema=schema_data)
    except ValidationError as e:
        raise ValueError(f"Invalid Authority Matrix structure: {e.message}") from e


def load_authority_matrix(repo_root: Path) -> dict:
    matrix_path = repo_root / "core" / "authority" / "authority-matrix.yaml"
    if not matrix_path.is_file():
        raise FileNotFoundError(f"Authority Matrix not found at {matrix_path}")
    with open(matrix_path, encoding="utf-8") as f:
        matrix_data = yaml.safe_load(f)
    validate_authority_matrix_data(matrix_data)
    return matrix_data


@dataclass(frozen=True)
class ExecutionAuthority:
    read_paths: ScopedAccess
    modify_paths: ScopedAccess
    terminal_commands: ScopedAccess
    network_allowed: bool


def get_execution_authority(matrix: dict, specialist_id: str) -> ExecutionAuthority:
    validate_authority_matrix_data(matrix)
    specialists = matrix.get("specialists", {})
    if specialist_id not in specialists:
        raise ValueError(f"Specialist '{specialist_id}' not found in Authority Matrix")

    spec = specialists[specialist_id]
    execution = spec["execution"]

    return ExecutionAuthority(
        normalize_access_scope(execution["read_paths"]),
        normalize_access_scope(execution["modify_paths"]),
        normalize_access_scope(execution["terminal_commands"]),
        execution.get("network_allowed", False),
    )


def path_allows(allowed: str, requested: str) -> bool:
    if fnmatch(requested, allowed):
        return True
    scope_dir = allowed.rstrip("*").rstrip("/")
    return bool(requested.startswith(scope_dir + "/") or requested == scope_dir)


def terminal_command_allows(allowed: str, requested: str) -> bool:
    return requested == allowed or requested.startswith(allowed + " ")


def scope_allows(maximum: ScopedAccess, requested: ScopedAccess, matcher) -> bool:
    if maximum.mode == AccessMode.DENY_ALL:
        return requested.mode == AccessMode.DENY_ALL
    elif maximum.mode == AccessMode.ALLOW_LIST:
        if requested.mode == AccessMode.DENY_ALL:
            return True
        if requested.mode == AccessMode.UNRESTRICTED:
            return False
        # requested ALLOW_LIST -> check subset
        for req_val in requested.values:
            if not any(matcher(max_val, req_val) for max_val in maximum.values):
                return False
        return True
    elif maximum.mode == AccessMode.UNRESTRICTED:
        return True
    return False


def network_allows(maximum: bool, requested: bool) -> bool:
    return not (requested and not maximum)
