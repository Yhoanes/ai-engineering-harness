from pathlib import Path

import yaml

from engine.advisor.models import AdvisorGuidance
from engine.projects.manager import inspect_project_state


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def discover_specialists(repo_root: Path) -> list[dict]:
    specs_dir = repo_root / "core" / "specialists"
    catalog = []
    if not specs_dir.exists():
        return catalog
    for p in specs_dir.rglob("specialist.yaml"):
        data = _load_yaml(p)
        catalog.append(
            {
                "id": data.get("id"),
                "display_name": data.get("display_name"),
                "description": data.get("description"),
                "category": data.get("category"),
                "purpose": data.get("purpose"),
                "capabilities": data.get("capabilities") or [],
                "limitations": data.get("limitations") or [],
                "authority_profile": data.get("authority_profile"),
                "task_capabilities": data.get("task_capabilities") or {},
                "context_requirements": data.get("context_requirements") or [],
                "output_contract": data.get("output_contract") or {},
                "escalation_rules": data.get("escalation_rules") or [],
            }
        )
    return catalog


def discover_workflows(repo_root: Path) -> list[dict]:
    wfs_dir = repo_root / "core" / "workflows"
    catalog = []
    if not wfs_dir.exists():
        return catalog
    for p in wfs_dir.rglob("workflow.yaml"):
        data = _load_yaml(p)
        catalog.append(
            {
                "id": data.get("id"),
                "display_name": data.get("display_name"),
                "description": data.get("description"),
                "purpose": data.get("purpose"),
                "allowed_specialists": data.get("allowed_specialists") or [],
                "entry_conditions": data.get("entry_conditions") or [],
                "steps": data.get("steps") or [],
                "required_validators": data.get("required_validators") or [],
                "evidence_requirements": data.get("evidence_requirements") or [],
                "exit_conditions": data.get("exit_conditions") or [],
                "next_workflows": data.get("next_workflows") or [],
                "forbidden_actions": data.get("forbidden_actions") or [],
            }
        )
    return catalog


def explain_blockers(lifecycle: str, warnings: list[str]) -> list[str]:
    blockers = []
    if lifecycle == "not_found":
        blockers.append("Project does not exist physically.")
    elif lifecycle == "inconsistent_markers":
        blockers.append("Inconsistent project markers. Manual review required.")

    for w in warnings:
        blockers.append(w)
    return blockers


def get_general_guidance(repo_root: Path, project_key: str | None = None) -> AdvisorGuidance:
    if not project_key:
        msg = (
            "Welcome to the AI Engineering Harness.\n"
            "Currently, no project is selected.\n"
            "You can create a project (requires a governed filesystem operation) "
            "to start working.\n"
            "I can explain available specialists, workflows, or governance rules."
        )
        return AdvisorGuidance(
            message=msg,
            project_key=None,
            lifecycle_state=None,
            current_phase=None,
            recommended_workflow=None,
            recommended_specialists=["general-advisor"],
            blockers=["no project yet"],
            requires_task_contract=False,
            requires_human_approval=False,
            next_user_action="Define project intent",
        )

    st = inspect_project_state(repo_root, project_key)
    blockers = explain_blockers(st.lifecycle, st.warnings)

    if st.lifecycle == "not_found":
        msg = (
            f"Project '{project_key}' is not physically initialized yet. "
            "A governed task is required to initialize it."
        )
        return AdvisorGuidance(
            message=msg,
            project_key=project_key,
            lifecycle_state=st.lifecycle,
            current_phase=st.current_phase,
            recommended_workflow=None,
            recommended_specialists=[],
            blockers=blockers,
            requires_task_contract=True,
            requires_human_approval=False,
            next_user_action="Initialize project",
        )

    req_contract = False
    next_action = "Create Task Contract"

    if st.lifecycle == "initialized":
        msg = (
            "Project is initialized but requirements are NOT_DEFINED. "
            "The next step is analyze-requirement."
        )
        req_contract = True
    elif st.lifecycle == "requirements_defined":
        msg = (
            "Requirements are DEFINED but architecture is not APPROVED. "
            "The next step is design-solution."
        )
        req_contract = True
    elif st.lifecycle == "architecture_defined":
        msg = "Architecture is APPROVED. You can now plan tasks for implementation."
        req_contract = True
    elif st.lifecycle == "implementation_started":
        msg = "Implementation is active. Consult Router/workflows for specific task execution."
        req_contract = True
    elif st.lifecycle == "inconsistent_markers":
        msg = "Project markers are inconsistent. Review required."
        next_action = "Review markers manually"
    else:
        msg = f"Unknown lifecycle state: {st.lifecycle}."

    return AdvisorGuidance(
        message=msg,
        project_key=project_key,
        lifecycle_state=st.lifecycle,
        current_phase=st.current_phase,
        recommended_workflow=st.recommended_next_workflow,
        recommended_specialists=["general-advisor"],
        blockers=blockers,
        requires_task_contract=req_contract,
        requires_human_approval=False,
        next_user_action=next_action,
    )


def _is_evolution_intent(request: str) -> bool:
    req = request.lower()

    # Negative checks (project work)
    if ("my application" in req or "my project" in req) and "harness" not in req:
        return False

    # Exact phrasing checks based on ACs
    if "improve the ai engineering harness itself" in req:
        return True
    if "reusable skill" in req:
        return True

    mentions_harness = "harness" in req

    # Check if they are asking to add/support host/provider/runtime/specialist
    extensions = [
        "host",
        "specialist",
        "workflow",
        "skill",
        "adapter",
        "provider",
        "local model",
        "runtime",
    ]
    mentions_extension = any(ext in req for ext in extensions)

    return bool(mentions_harness and mentions_extension)


def get_guidance_for_request(
    repo_root: Path, user_request: str, project_key: str | None = None
) -> AdvisorGuidance:
    """
    Public API that incorporates Intent Classification.
    If the request is an evolution intent, routes to harness-evolution-advisor.
    Otherwise, falls back to get_general_guidance.
    """
    if _is_evolution_intent(user_request):
        specs = discover_specialists(repo_root)
        installed = any(s.get("id") == "harness-evolution-advisor" for s in specs)

        if not installed:
            return AdvisorGuidance(
                message=(
                    "Evolution intent detected, but Harness Evolution Advisor is not installed."
                ),
                project_key=project_key,
                lifecycle_state=None,
                current_phase=None,
                recommended_workflow=None,
                recommended_specialists=[],
                blockers=["EVOLUTION_ADVISOR_NOT_INSTALLED"],
                requires_task_contract=False,
                requires_human_approval=False,
                next_user_action="Install harness-evolution-advisor extension.",
            )

        return AdvisorGuidance(
            message=(
                "Evolution intent detected. The Harness Evolution Advisor can "
                "help you design this extension safely."
            ),
            project_key=project_key,
            lifecycle_state=None,
            current_phase=None,
            recommended_workflow="discuss",
            recommended_specialists=["harness-evolution-advisor"],
            blockers=[],
            requires_task_contract=False,
            requires_human_approval=True,  # All actual implementations require approval
            next_user_action="Describe the improvement you want to make to the Harness.",
        )

    # Fallback to the original logic
    return get_general_guidance(repo_root, project_key)
