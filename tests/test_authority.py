from __future__ import annotations

from engine.validators.validate_authority import validate


def test_valid_specialist_authority(
    valid_standard_task: dict, sample_authority_matrix: dict
) -> None:
    result = validate(
        "backend-engineer", valid_standard_task, authority_matrix=sample_authority_matrix
    )
    assert result.valid, f"Errors: {result.errors}"


def test_unknown_specialist(valid_standard_task: dict, sample_authority_matrix: dict) -> None:
    result = validate("unknown-role", valid_standard_task, authority_matrix=sample_authority_matrix)
    assert not result.valid
    assert any("not found" in e for e in result.errors)


def test_empty_specialist_id(valid_standard_task: dict) -> None:
    result = validate("", valid_standard_task)
    assert not result.valid
    assert any("empty" in e for e in result.errors)


def test_no_authority_matrix_warns(
    valid_standard_task: dict,
) -> None:
    result = validate("backend-engineer", valid_standard_task, authority_matrix=None)
    assert result.valid  # Warning only
    assert len(result.warnings) > 0


def test_specialist_with_no_modify_scope(
    valid_standard_task: dict, sample_authority_matrix: dict
) -> None:
    result = validate(
        "code-reviewer", valid_standard_task, authority_matrix=sample_authority_matrix
    )
    assert not result.valid
    assert any("DENY_ALL modify permissions" in e for e in result.errors)


def test_forbidden_actions_enforced(
    valid_standard_task: dict, sample_authority_matrix: dict
) -> None:
    """Every specialist must have approve_task, accept_task, close_task in forbidden."""
    result = validate(
        "backend-engineer", valid_standard_task, authority_matrix=sample_authority_matrix
    )
    assert result.valid  # backend-engineer has all three forbidden


def test_orchestrator_can_create_task(
    sample_authority_matrix: dict,
) -> None:
    """Orchestrator is the only role with create_task: true."""
    orch = sample_authority_matrix["specialists"]["orchestrator"]
    assert orch["task_management"]["create_task"] is True

    be = sample_authority_matrix["specialists"]["backend-engineer"]
    assert be["task_management"]["create_task"] is False


def test_specialist_with_deny_all_task(
    valid_standard_task: dict, sample_authority_matrix: dict
) -> None:
    valid_standard_task["scope"]["planned_paths"]["modify"] = {"mode": "deny_all"}
    # Even if specialist has no modify scope, it's valid because the task is DENY_ALL
    sample_authority_matrix["specialists"]["backend-engineer"]["modify"]["scope"] = []

    result = validate(
        specialist_id="backend-engineer",
        task=valid_standard_task,
        authority_matrix=sample_authority_matrix,
    )
    assert result.valid


def test_unrestricted_rejected_even_with_limited_scope(
    valid_standard_task: dict, sample_authority_matrix: dict
) -> None:
    from engine.validators.validate_authority import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {"mode": "unrestricted"}
    sample_authority_matrix["specialists"]["backend-engineer"]["modify"]["scope"] = [
        "src/backend/**"
    ]
    result = validate(
        "backend-engineer", valid_standard_task, authority_matrix=sample_authority_matrix
    )
    assert not result.valid
    assert "Task requires explicit UNRESTRICTED modify authority" in result.errors[0]


def test_unrestricted_rejected_even_with_wildcard(
    valid_standard_task: dict, sample_authority_matrix: dict
) -> None:
    from engine.validators.validate_authority import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {"mode": "unrestricted"}
    sample_authority_matrix["specialists"]["backend-engineer"]["modify"]["scope"] = ["**"]
    result = validate(
        "backend-engineer", valid_standard_task, authority_matrix=sample_authority_matrix
    )
    assert not result.valid
    assert "Task requires explicit UNRESTRICTED modify authority" in result.errors[0]


def test_allow_list_historical_matching_preserved(
    valid_standard_task: dict, sample_authority_matrix: dict
) -> None:
    from engine.validators.validate_authority import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {
        "mode": "allow_list",
        "values": ["src/backend/a.py"],
    }
    sample_authority_matrix["specialists"]["backend-engineer"]["modify"]["scope"] = [
        "src/backend/**"
    ]
    result = validate(
        "backend-engineer", valid_standard_task, authority_matrix=sample_authority_matrix
    )
    assert result.valid


def test_unrestricted_rejected_as_unsupported_even_with_no_matrix(
    valid_standard_task: dict,
) -> None:
    from engine.validators.validate_authority import validate

    valid_standard_task["scope"]["planned_paths"]["modify"] = {"mode": "unrestricted"}
    result = validate("backend-engineer", valid_standard_task, authority_matrix=None)
    assert not result.valid
    assert "Task requires explicit UNRESTRICTED modify authority" in result.errors[0]


def test_validate_network_allows(sample_authority_matrix, valid_standard_task):
    from engine.validators.validate_authority import validate

    # Baseline: Matrix False, Task missing (False) -> valid
    sample_authority_matrix["specialists"]["backend-engineer"]["execution"]["network_allowed"] = (
        False
    )
    if "network_allowed" in valid_standard_task["scope"]["allowed_actions"]:
        del valid_standard_task["scope"]["allowed_actions"]["network_allowed"]
    res = validate(
        "backend-engineer", valid_standard_task, authority_matrix=sample_authority_matrix
    )
    assert res.valid

    # Task explicitly False -> valid
    valid_standard_task["scope"]["allowed_actions"]["network_allowed"] = False
    res = validate(
        "backend-engineer", valid_standard_task, authority_matrix=sample_authority_matrix
    )
    assert res.valid

    # Task True, Matrix False -> invalid
    valid_standard_task["scope"]["allowed_actions"]["network_allowed"] = True
    res = validate(
        "backend-engineer", valid_standard_task, authority_matrix=sample_authority_matrix
    )
    assert not res.valid
    assert any("does not grant network_allowed" in e for e in res.errors)

    # Matrix True, Task False -> valid
    sample_authority_matrix["specialists"]["backend-engineer"]["execution"]["network_allowed"] = (
        True
    )
    valid_standard_task["scope"]["allowed_actions"]["network_allowed"] = False
    res = validate(
        "backend-engineer", valid_standard_task, authority_matrix=sample_authority_matrix
    )
    assert res.valid

    # Matrix True, Task True -> valid
    valid_standard_task["scope"]["allowed_actions"]["network_allowed"] = True
    res = validate(
        "backend-engineer", valid_standard_task, authority_matrix=sample_authority_matrix
    )
    assert res.valid
