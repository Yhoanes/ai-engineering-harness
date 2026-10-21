from __future__ import annotations

from pathlib import Path

from .models import RouteDecision
from .specialist_selector import determine_specialist


def _check_exists(repo_root: Path, type_dir: str, entity_id: str) -> bool:
    return (repo_root / "core" / type_dir / entity_id).is_dir()


def route_request(
    intent: str, task_contract: dict | None = None, repo_root: Path | None = None
) -> RouteDecision:
    """
    Deterministically recommend a RouteDecision based on intent and task state.
    Does NOT grant authorization.
    """
    intent_lower = intent.lower()

    # 1. Ambiguity detection
    if "ambiguous" in intent_lower:
        return RouteDecision(
            workflow_id="discuss",
            primary_specialist="general-advisor",
            confidence=0.0,
            reasoning_summary="Intent is ambiguous.",
            unresolved_ambiguities=["Clarify intent"],
        )

    # Pre-calculate Workflow ID
    workflow_id = "discuss"
    context_level = 0
    requires_contract = False

    if task_contract:
        status = task_contract.get("status")
        approval_status = task_contract.get("approval_status")

        if "close" in intent_lower or "accept" in intent_lower:
            workflow_id = "close-task"
            context_level = 2
        elif "implement" in intent_lower:
            if status in ("approved", "in_progress") and approval_status == "approved":
                workflow_id = "implement-task"
                context_level = 2
            elif (status == "approved" and approval_status != "approved") or (
                status == "awaiting_approval"
            ):
                workflow_id = "approve-task"
                context_level = 2
            else:
                workflow_id = "plan-task"
                context_level = 1
                requires_contract = True
        elif "approve" in intent_lower or status == "awaiting_approval":
            workflow_id = "approve-task"
            context_level = 2
    else:
        # Request without contract
        if "implement" in intent_lower:
            workflow_id = "plan-task"
            context_level = 1
            requires_contract = True
        elif "review" in intent_lower:
            workflow_id = "security-review" if "security" in intent_lower else "review-task"
            context_level = 1
        elif "debug" in intent_lower:
            workflow_id = "debug-task"
            context_level = 1
        elif "performance" in intent_lower:
            workflow_id = "performance-review"
            context_level = 1
        elif "document" in intent_lower:
            workflow_id = "document-task"
            context_level = 1
        elif "release" in intent_lower:
            workflow_id = "release-task"
            context_level = 1
        elif "new-project" in intent_lower:
            workflow_id = "discuss"
            context_level = 0

    specialist = None

    if workflow_id in ("plan-task", "approve-task", "close-task"):
        specialist = "orchestrator"
    elif repo_root:
        # Respect existing assignment if already approved
        if task_contract:
            is_app = task_contract.get("status") == "approved"
            is_app_st = task_contract.get("approval_status") == "approved"
            if is_app and is_app_st:
                assigned = task_contract.get("assigned_specialists", [])
                if assigned and isinstance(assigned, list) and len(assigned) > 0:
                    specialist = assigned[0]

        # If not pre-assigned, calculate it
        if not specialist:
            specialist = determine_specialist(
                intent, task_contract, repo_root, workflow_id=workflow_id
            )

    if not specialist:
        if workflow_id == "discuss":
            specialist = "general-advisor"
        else:
            # Escalation
            return RouteDecision(
                workflow_id="discuss",
                primary_specialist="general-advisor",
                context_level=0,
                confidence=0.0,
                reasoning_summary=(
                    f"Escalation required. Could not determine valid specialist for {workflow_id}."
                ),
                unresolved_ambiguities=[f"Determine specialist for {workflow_id}"],
            )

    rs = ""
    if task_contract:
        if "close" in intent_lower or "accept" in intent_lower:
            rs = "User requested closure of existing task."
        elif "implement" in intent_lower:
            if (
                task_contract.get("status") == "approved"
                and task_contract.get("approval_status") == "approved"
            ):
                rs = "Approved task ready for implementation."
            elif workflow_id == "plan-task":
                rs = "Cannot implement without approved contract."
        elif workflow_id == "approve-task":
            if (task_contract and task_contract.get("status") == "approved"
                and task_contract.get("approval_status") != "approved"):
                rs = "Task is approved but lacks valid approval_status."
            else:
                rs = "Task is awaiting approval."
    else:
        if "implement" in intent_lower:
            rs = "Implementation requested without a contract."
        elif "review" in intent_lower:
            if "security" in intent_lower:
                rs = "Security review requested."
            else:
                rs = "Code review requested."
        elif "debug" in intent_lower:
            rs = "Debugging requested."
        elif "performance" in intent_lower:
            rs = "Performance review requested."
        elif "document" in intent_lower:
            rs = "Documentation requested."
        elif "release" in intent_lower:
            rs = "Release operations requested."
        else:
            if workflow_id == "discuss":
                rs = "Conversational intent. Defaulting to discuss."
            else:
                rs = f"{workflow_id} requested."

    return RouteDecision(
        workflow_id=workflow_id,
        primary_specialist=specialist,
        context_level=context_level,
        requires_task_contract=requires_contract,
        reasoning_summary=rs,
    )
