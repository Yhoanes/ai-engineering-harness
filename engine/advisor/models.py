from dataclasses import dataclass


@dataclass
class AdvisorGuidance:
    message: str
    project_key: str | None
    lifecycle_state: str | None
    current_phase: str | None
    recommended_workflow: str | None
    recommended_specialists: list[str]
    blockers: list[str]
    requires_task_contract: bool
    requires_human_approval: bool
    next_user_action: str | None
