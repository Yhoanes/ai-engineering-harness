from __future__ import annotations

from engine.validators.validate_allowed_paths_pre import validate


def test_paths_within_scope(valid_standard_task: dict, sample_authority_matrix: dict) -> None:
    # Only backend-engineer has src/** scope; qa-engineer has tests/** scope
    valid_standard_task["assigned_specialists"] = ["backend-engineer"]
    result = validate(valid_standard_task, authority_matrix=sample_authority_matrix)
    assert result.valid, f"Errors: {result.errors}"


def test_paths_outside_authority(valid_standard_task: dict, sample_authority_matrix: dict) -> None:
    valid_standard_task["scope"]["planned_paths"]["modify"] = [
        "projects/analista/config/secret.yaml"  # Outside src/**
    ]
    result = validate(valid_standard_task, authority_matrix=sample_authority_matrix)
    assert not result.valid
    assert any("exceed authority" in e for e in result.errors)


def test_empty_planned_paths(valid_standard_task: dict) -> None:
    # Empty paths is normalized to DENY_ALL which is INVALID for mutational precheck
    valid_standard_task["scope"]["planned_paths"]["modify"] = []
    result = validate(valid_standard_task)
    assert not result.valid
    assert any("DENY_ALL" in e for e in result.errors)


def test_unrestricted_rejected_as_unsupported(valid_standard_task: dict) -> None:
    valid_standard_task["scope"]["planned_paths"]["modify"] = {"mode": "unrestricted"}
    valid_standard_task["assigned_specialists"] = ["backend-engineer"]
    matrix = {
        "specialists": {
            "backend-engineer": {
                "execution": {
                    "modify_paths": {"mode": "allow_list", "values": ["**"]},
                    "read_paths": {"mode": "deny_all"},
                    "terminal_commands": {"mode": "deny_all"},
                    "network_allowed": False,
                }
            }
        }
    }
    result = validate(valid_standard_task, authority_matrix=matrix)
    assert not result.valid
    assert any(
        "only has ALLOW_LIST" in e
        or "DENY_ALL modify permissions" in e
        or "no Authority Matrix was provided to grant it" in e
        for e in result.errors
    )


def test_no_authority_matrix_warns(valid_standard_task: dict) -> None:
    result = validate(valid_standard_task, authority_matrix=None)
    assert result.valid  # Passes with warning
    assert len(result.warnings) > 0


def test_specialist_with_no_modify_scope(
    valid_standard_task: dict, sample_authority_matrix: dict
) -> None:
    valid_standard_task["assigned_specialists"] = ["code-reviewer"]
    result = validate(valid_standard_task, authority_matrix=sample_authority_matrix)
    assert not result.valid
    assert any("DENY_ALL modify permissions" in e for e in result.errors)


def test_unrestricted_rejected_as_unsupported_even_with_no_matrix(
    valid_standard_task: dict,
) -> None:
    from engine.validators.validate_allowed_paths_pre import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {"mode": "unrestricted"}
    result = validate(valid_standard_task, authority_matrix=None)
    assert not result.valid
    assert any(
        "only has ALLOW_LIST" in e
        or "DENY_ALL modify permissions" in e
        or "no Authority Matrix was provided to grant it" in e
        for e in result.errors
    )
