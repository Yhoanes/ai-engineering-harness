from pathlib import Path

import pytest

from engine.router import route_request


@pytest.fixture
def repo_root():
    return Path(__file__).parent.parent

def test_route_implement_no_contract():
    decision = route_request("implement the feature", task_contract=None)
    assert decision.workflow_id == "plan-task"

def test_route_implement_awaiting_approval():
    contract = {"status": "awaiting_approval", "approval_status": "pending"}
    decision = route_request("implement the feature", task_contract=contract)
    assert decision.workflow_id == "approve-task"

def test_route_implement_approved_and_approved_status(repo_root):
    contract = {
        "status": "approved",
        "approval_status": "approved",
        "assigned_specialists": ["backend-engineer"]
    }
    decision = route_request("implement the feature", task_contract=contract, repo_root=repo_root)
    assert decision.workflow_id == "implement-task"
    assert decision.primary_specialist == "backend-engineer"

def test_route_implement_approved_but_pending_approval_status():
    contract = {"status": "approved", "approval_status": "pending"}
    decision = route_request("implement the feature", task_contract=contract)
    assert decision.workflow_id == "approve-task"

def test_route_implement_approved_but_rejected_approval_status():
    contract = {"status": "approved", "approval_status": "rejected"}
    decision = route_request("implement the feature", task_contract=contract)
    assert decision.workflow_id == "approve-task"

def test_route_ambiguous():
    decision = route_request("This is ambiguous")
    assert decision.workflow_id == "discuss"
    assert decision.confidence == 0.0
    assert "Clarify intent" in decision.unresolved_ambiguities

# Dynamic delegation tests
def test_dynamic_selection_backend(repo_root):
    contract = {
        "status": "approved",
        "approval_status": "approved",
        "description": "implement the backend business logic and api"
    }
    decision = route_request("implement", task_contract=contract, repo_root=repo_root)
    assert decision.primary_specialist == "backend-engineer"

def test_dynamic_selection_frontend(repo_root):
    contract = {
        "status": "approved",
        "approval_status": "approved",
        "description": "implement frontend user interfaces and component"
    }
    decision = route_request("implement", task_contract=contract, repo_root=repo_root)
    assert decision.primary_specialist == "frontend-engineer"

def test_dynamic_selection_database(repo_root):
    contract = {
        "status": "approved",
        "approval_status": "approved",
        "description": "implement database schema migration"
    }
    decision = route_request("implement", task_contract=contract, repo_root=repo_root)
    assert decision.primary_specialist == "database-engineer"

def test_dynamic_selection_security(repo_root):
    decision = route_request("review security vulnerability", repo_root=repo_root)
    assert decision.primary_specialist == "security-engineer"
    assert decision.workflow_id == "security-review"

def test_dynamic_selection_documentation(repo_root):
    decision = route_request("write documentation readme", repo_root=repo_root)
    assert decision.primary_specialist == "documentation-engineer"
    assert decision.workflow_id == "document-task"

def test_dynamic_selection_release(repo_root):
    decision = route_request("deploy release pipeline", repo_root=repo_root)
    assert decision.primary_specialist == "devops-release-engineer"
    assert decision.workflow_id == "release-task"

def test_dynamic_selection_tie_escalates(repo_root):
    # Has both frontend and backend keywords
    contract = {
        "status": "approved",
        "approval_status": "approved",
        "description": "implement backend frontend"
    }
    decision = route_request("implement", task_contract=contract, repo_root=repo_root)
    assert decision.workflow_id == "discuss"
    assert decision.primary_specialist == "general-advisor"
    assert "escalation required" in decision.reasoning_summary.lower()
    assert decision.primary_specialist == "general-advisor"
    assert "escalation required" in decision.reasoning_summary.lower()

def test_dynamic_selection_low_confidence_escalates(repo_root):
    contract = {"status": "approved", "approval_status": "approved", "description": "do stuff"}
    decision = route_request("implement", task_contract=contract, repo_root=repo_root)
    assert decision.workflow_id == "discuss"
    assert decision.primary_specialist == "general-advisor"
    assert "escalation required" in decision.reasoning_summary.lower()

def test_dynamic_selection_unauthorized_specialist_escalates(repo_root):
    # Intent is implement, so workflow_id = implement-task
    # Keywords match code-reviewer ("code review").
    # code-reviewer is NOT authorized for implement-task in workflow.yaml.
    contract = {
        "status": "approved",
        "approval_status": "approved",
        "description": "code review"
    }
    decision = route_request("implement", task_contract=contract, repo_root=repo_root)

    # Should escalate because no authorized specialist could be found for implement-task
    assert decision.workflow_id == "discuss"
    assert decision.primary_specialist == "general-advisor"
    assert "escalation required" in decision.reasoning_summary.lower()

def test_dynamic_selection_preserves_pre_approved(repo_root):
    contract = {
        "status": "approved",
        "approval_status": "approved",
        "assigned_specialists": ["database-engineer"],
        "description": "frontend user interface" # Should be ignored because of pre-approved
    }
    decision = route_request("implement", task_contract=contract, repo_root=repo_root)
    assert decision.workflow_id == "implement-task"
    assert decision.primary_specialist == "database-engineer"

def test_new_project_is_read_only(repo_root):
    decision = route_request("/new-project", repo_root=repo_root)
    # the default fallback is discuss / general-advisor
    assert decision.workflow_id == "discuss"
    assert decision.primary_specialist == "general-advisor"
