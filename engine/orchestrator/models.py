from dataclasses import dataclass, field

from engine.context.models import ContextBundle


@dataclass(frozen=True)
class OrchestratorHandoff:
    project: str
    workflow: str
    primary_specialist: str
    supporting_specialists: list[str] = field(default_factory=list)
    context_bundle: ContextBundle | None = None
    task_contract: dict | None = None
    restrictions: list[str] = field(default_factory=list)
    next_action: str = ""
