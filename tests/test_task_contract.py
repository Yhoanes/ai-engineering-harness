from __future__ import annotations

import pytest

from engine.validators.validate_task_contract import validate


def test_valid_standard_task(valid_standard_task: dict) -> None:
    result = validate(valid_standard_task)
    assert result.valid, f"Expected valid, got errors: {result.errors}"


def test_valid_light_task(valid_light_task: dict) -> None:
    result = validate(valid_light_task)
    assert result.valid, f"Expected valid, got errors: {result.errors}"


def test_missing_task_id(valid_standard_task: dict) -> None:
    del valid_standard_task["task_id"]
    result = validate(valid_standard_task)
    assert not result.valid
    assert any("task_id" in e for e in result.errors)


def test_invalid_status_value(valid_standard_task: dict) -> None:
    valid_standard_task["status"] = "invalid_status"
    result = validate(valid_standard_task)
    assert not result.valid


def test_invalid_approval_status(valid_standard_task: dict) -> None:
    valid_standard_task["approval_status"] = "maybe"
    result = validate(valid_standard_task)
    assert not result.valid


def test_approval_consistency_approved_without_by(
    valid_standard_task: dict,
) -> None:
    valid_standard_task["approval_status"] = "approved"
    valid_standard_task["approved_by"] = None
    valid_standard_task["approved_at"] = None
    result = validate(valid_standard_task)
    assert not result.valid
    assert any("approved_by" in e for e in result.errors)


def test_empty_modify_paths(valid_standard_task: dict) -> None:
    valid_standard_task["scope"]["planned_paths"]["modify"] = []
    result = validate(valid_standard_task)
    assert not result.valid


def test_empty_assigned_specialists_allowed_in_draft(valid_standard_task: dict) -> None:
    valid_standard_task["status"] = "awaiting_approval"
    valid_standard_task["approval_status"] = "pending"
    valid_standard_task["approved_by"] = None
    valid_standard_task["approved_at"] = None
    valid_standard_task["assigned_specialists"] = []
    result = validate(valid_standard_task)
    assert result.valid


def test_empty_assigned_specialists_rejected_in_approved(valid_standard_task: dict) -> None:
    valid_standard_task["status"] = "approved"
    valid_standard_task["approval_status"] = "approved"
    valid_standard_task["approved_by"] = "User"
    valid_standard_task["approved_at"] = "2026-08-30T10:00:00Z"
    valid_standard_task["assigned_specialists"] = []
    result = validate(valid_standard_task)
    assert not result.valid
    assert any("assigned_specialists cannot be empty" in e for e in result.errors)


def test_task_with_deviation(valid_task_with_deviation: dict) -> None:
    result = validate(valid_task_with_deviation)
    assert result.valid, f"Expected valid, got errors: {result.errors}"


def test_invalid_task_id_format(valid_standard_task: dict) -> None:
    valid_standard_task["task_id"] = "task-1"  # Wrong format
    result = validate(valid_standard_task)
    assert not result.valid


# ─── Task ID Pattern Tests (AC-01, AC-02, AC-05, AC-06) ───


def test_task_id_pattern_task_xxxx(valid_standard_task: dict) -> None:
    """TASK-0001 should be a valid task_id."""
    valid_standard_task["task_id"] = "TASK-0001"
    result = validate(valid_standard_task)
    assert result.valid, f"TASK-0001 should be valid: {result.errors}"


def test_task_id_pattern_harness_xxxx(valid_standard_task: dict) -> None:
    """HARNESS-0001 should be a valid task_id."""
    valid_standard_task["task_id"] = "HARNESS-0001"
    result = validate(valid_standard_task)
    assert result.valid, f"HARNESS-0001 should be valid: {result.errors}"


def test_task_id_pattern_harness_bootstrap_xxxx(valid_standard_task: dict) -> None:
    """HARNESS-BOOTSTRAP-0001 should be a valid task_id."""
    valid_standard_task["task_id"] = "HARNESS-BOOTSTRAP-0001"
    result = validate(valid_standard_task)
    assert result.valid, f"HARNESS-BOOTSTRAP-0001 should be valid: {result.errors}"


@pytest.mark.parametrize(
    "bad_id",
    [
        "task-0001",  # lowercase
        "TASK0001",  # missing hyphen
        "HARNESS0001",  # missing hyphen
        "TASK-1",  # too few digits
        "TASK-00001",  # too many digits
        "FOO-0001",  # wrong prefix
        "HARNESS-BOOT-0001",  # wrong middle segment
        "",  # empty
    ],
)
def test_task_id_rejects_invalid_formats(valid_standard_task: dict, bad_id: str) -> None:
    """Invalid task IDs should be rejected."""
    valid_standard_task["task_id"] = bad_id
    result = validate(valid_standard_task)
    assert not result.valid, f"Expected '{bad_id}' to be rejected"


def test_explicit_deny_all_valid(valid_standard_task: dict) -> None:
    from engine.validators.validate_task_contract import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {"mode": "deny_all"}
    res = validate(valid_standard_task)
    assert res.valid


def test_explicit_unrestricted_valid(valid_standard_task: dict) -> None:
    from engine.validators.validate_task_contract import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {"mode": "unrestricted"}
    res = validate(valid_standard_task)
    assert res.valid


def test_explicit_allow_list_valid(valid_standard_task: dict) -> None:
    from engine.validators.validate_task_contract import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {
        "mode": "allow_list",
        "values": ["src/a.py"],
    }
    res = validate(valid_standard_task)
    assert res.valid


def test_explicit_deny_all_with_values_invalid(valid_standard_task: dict) -> None:
    from engine.validators.validate_task_contract import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {
        "mode": "deny_all",
        "values": ["src/a.py"],
    }
    res = validate(valid_standard_task)
    assert not res.valid


def test_explicit_unrestricted_with_values_invalid(valid_standard_task: dict) -> None:
    from engine.validators.validate_task_contract import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {
        "mode": "unrestricted",
        "values": ["src/a.py"],
    }
    res = validate(valid_standard_task)
    assert not res.valid


def test_explicit_allow_list_missing_values_invalid(valid_standard_task: dict) -> None:
    from engine.validators.validate_task_contract import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {"mode": "allow_list"}
    res = validate(valid_standard_task)
    assert not res.valid


def test_explicit_allow_list_empty_values_invalid(valid_standard_task: dict) -> None:
    from engine.validators.validate_task_contract import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {"mode": "allow_list", "values": []}
    res = validate(valid_standard_task)
    assert not res.valid


def test_unknown_mode_invalid(valid_standard_task: dict) -> None:
    from engine.validators.validate_task_contract import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {"mode": "unknown"}
    res = validate(valid_standard_task)
    assert not res.valid


def test_historical_contracts_baseline_comparison():
    import subprocess

    import pytest
    import yaml
    from jsonschema import Draft7Validator

    from engine.execution.models import AccessMode
    from engine.validators import validate_task_contract
    from engine.validators.scope import normalize_access_scope

    baseline_schema_str = subprocess.run(
        ["git", "show", "HEAD:core/schemas/task-contract.schema.yaml"],
        capture_output=True,
        text=True,
    ).stdout
    baseline_schema = yaml.safe_load(baseline_schema_str)
    baseline_validator = Draft7Validator(baseline_schema)

    tracked_files_output = subprocess.run(
        ["git", "ls-files", ".harness/projects/**/*.yaml"], capture_output=True, text=True
    ).stdout
    tracked_files = [
        f.strip() for f in tracked_files_output.splitlines() if f.strip() and "tasks/" in f
    ]

    _ = len(tracked_files)
    valid_baseline = 0
    invalid_baseline = 0
    valid_after = 0
    implicit_expansions = 0

    for f in tracked_files:
        try:
            with open(f, encoding="utf-8") as fp:
                data = yaml.safe_load(fp)
        except Exception:
            invalid_baseline += 1
            continue

        is_baseline_valid = True
        for _ in baseline_validator.iter_errors(data):
            is_baseline_valid = False
            break

        if is_baseline_valid:
            valid_baseline += 1
            res = validate_task_contract.validate(data)
            if res.valid:
                valid_after += 1
            else:
                pytest.fail(
                    f"Contract {f} was valid under baseline but is now invalid: {res.errors}"
                )

            modify = data.get("scope", {}).get("planned_paths", {}).get("modify", [])
            norm = normalize_access_scope(modify)
            if norm.mode == AccessMode.UNRESTRICTED:
                implicit_expansions += 1
                pytest.fail(f"Contract {f} implicitly expanded to UNRESTRICTED!")
        else:
            invalid_baseline += 1

    assert valid_baseline == valid_after
    assert implicit_expansions == 0


def test_legacy_modify_empty_is_invalid(valid_standard_task: dict) -> None:
    from engine.validators.validate_task_contract import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = []
    res = validate(valid_standard_task)
    assert not res.valid


def test_legacy_read_empty_is_valid(valid_standard_task: dict) -> None:
    from engine.validators.validate_task_contract import validate

    valid_standard_task["scope"]["planned_paths"]["read"] = []
    res = validate(valid_standard_task)
    assert res.valid


def test_legacy_terminal_empty_is_valid(valid_standard_task: dict) -> None:
    from engine.validators.validate_task_contract import validate

    valid_standard_task["scope"]["allowed_actions"]["terminal"] = []
    res = validate(valid_standard_task)
    assert res.valid


def test_light_schema_explicit_modes(valid_light_task: dict) -> None:
    from engine.validators.validate_task_contract import validate

    # Deny all
    valid_light_task["scope"]["planned_paths"]["modify"] = {"mode": "deny_all"}
    assert validate(valid_light_task).valid

    # Unrestricted
    valid_light_task["scope"]["planned_paths"]["modify"] = {"mode": "unrestricted"}
    assert validate(valid_light_task).valid

    # Allow list
    valid_light_task["scope"]["planned_paths"]["modify"] = {
        "mode": "allow_list",
        "values": ["a.py"],
    }
    assert validate(valid_light_task).valid

    # Invalid combo
    valid_light_task["scope"]["planned_paths"]["modify"] = {"mode": "deny_all", "values": ["a.py"]}
    assert not validate(valid_light_task).valid


def test_task_contract_network_allowed(valid_standard_task):
    from engine.validators.validate_task_contract import validate

    # Missing is valid
    if "network_allowed" in valid_standard_task["scope"]["allowed_actions"]:
        del valid_standard_task["scope"]["allowed_actions"]["network_allowed"]
    validate(valid_standard_task)

    # False is valid
    valid_standard_task["scope"]["allowed_actions"]["network_allowed"] = False
    validate(valid_standard_task)

    # True is valid
    valid_standard_task["scope"]["allowed_actions"]["network_allowed"] = True
    validate(valid_standard_task)

    # Invalid types
    valid_standard_task["scope"]["allowed_actions"]["network_allowed"] = "true"
    assert not validate(valid_standard_task).valid

    valid_standard_task["scope"]["allowed_actions"]["network_allowed"] = None
    assert not validate(valid_standard_task).valid

    valid_standard_task["scope"]["allowed_actions"]["network_allowed"] = []
    assert not validate(valid_standard_task).valid
