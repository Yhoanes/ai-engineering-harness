from __future__ import annotations

from engine.validators.validate_preconditions import (
    DEFAULT_PRECONDITIONS,
    validate,
)

# Synthetic workflow definitions for testing
# (real workflows will be created in a post-bootstrap task)
SYNTHETIC_WORKFLOWS = {
    "implement-task": {
        "preconditions": [
            {"field": "status", "equals": "approved"},
            {"field": "approval_status", "equals": "approved"},
        ],
    },
    "close-task": {
        "preconditions": [
            {"field": "status", "equals": "in_progress"},
            {"field": "acceptance_status", "one_of": "passed,passed_with_deviation"},
        ],
    },
}


def test_implement_requires_approved(valid_standard_task: dict) -> None:
    """implement-task requires status=approved and approval_status=approved."""
    task = {**valid_standard_task, "status": "approved", "assigned_workflow": "implement-task"}
    result = validate(task, workflows=SYNTHETIC_WORKFLOWS)
    assert result.valid, f"Errors: {result.errors}"


def test_implement_blocks_when_not_approved(
    valid_standard_task: dict,
) -> None:
    task = {**valid_standard_task, "status": "draft", "assigned_workflow": "implement-task"}
    result = validate(task, workflows=SYNTHETIC_WORKFLOWS)
    assert not result.valid
    assert any("approved" in e for e in result.errors)


def test_close_requires_acceptance(
    valid_standard_task: dict,
) -> None:
    task = {
        **valid_standard_task,
        "status": "in_progress",
        "acceptance_status": "pending",
        "assigned_workflow": "close-task",
    }
    result = validate(task, workflows=SYNTHETIC_WORKFLOWS)
    assert not result.valid
    assert any("acceptance_status" in e for e in result.errors)


def test_close_passes_with_acceptance(
    valid_standard_task: dict,
) -> None:
    task = {
        **valid_standard_task,
        "status": "in_progress",
        "acceptance_status": "passed",
        "assigned_workflow": "close-task",
    }
    result = validate(task, workflows=SYNTHETIC_WORKFLOWS)
    assert result.valid


def test_no_workflow_warns(valid_standard_task: dict) -> None:
    task = {**valid_standard_task, "assigned_workflow": None}
    result = validate(task)
    assert result.valid  # Warning, not error
    assert len(result.warnings) > 0


def test_default_preconditions_exist() -> None:
    """Default preconditions should cover key workflows."""
    assert "implement-task" in DEFAULT_PRECONDITIONS
    assert "close-task" in DEFAULT_PRECONDITIONS
    assert "approve-task" in DEFAULT_PRECONDITIONS


def test_unknown_workflow_warns(valid_standard_task: dict) -> None:
    task = {**valid_standard_task, "assigned_workflow": "nonexistent-workflow"}
    result = validate(task, workflows={})
    assert result.valid  # Unknown = warning, no preconditions to check
