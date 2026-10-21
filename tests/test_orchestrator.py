from pathlib import Path

import pytest

from engine.orchestrator.orchestrator import next_task_id, prepare_handoff
from engine.router.models import RouteDecision
from engine.validators.validate_task_contract import validate


def test_next_task_id():
    assert next_task_id([]) == "TASK-0001"
    assert next_task_id(["TASK-0001", "TASK-0002"]) == "TASK-0003"
    assert next_task_id(["TASK-0042"]) == "TASK-0043"
    assert next_task_id([], prefix="HARNESS") == "HARNESS-0001"

    with pytest.raises(ValueError):
        next_task_id([], prefix="INVALID PREFIX")


def test_prepare_handoff_invalid_workflow():
    repo = Path(__file__).parent.parent
    decision = RouteDecision("nonexistent", "general-advisor")
    with pytest.raises(ValueError, match="Workflow nonexistent"):
        prepare_handoff(decision, "_harness-internal", repo)


def test_prepare_handoff_invalid_specialist():
    repo = Path(__file__).parent.parent
    decision = RouteDecision("discuss", "nonexistent")
    with pytest.raises(ValueError, match="Specialist nonexistent"):
        prepare_handoff(decision, "_harness-internal", repo)


def test_prepare_handoff_draft_contract():
    repo = Path(__file__).parent.parent
    decision = RouteDecision("plan-task", "orchestrator")
    handoff = prepare_handoff(decision, "_harness-internal", repo, ["TASK-0005"])
    assert handoff.workflow == "plan-task"
    assert handoff.task_contract is not None
    assert handoff.task_contract["task_id"] == "TASK-0006"
    assert handoff.task_contract["status"] == "awaiting_approval"

    # Validates against schema
    result = validate(handoff.task_contract)
    assert result.valid is True
