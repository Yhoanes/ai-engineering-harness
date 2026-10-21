from dataclasses import dataclass, field


@dataclass(frozen=True)
class RouteDecision:
    workflow_id: str
    primary_specialist: str
    supporting_specialists: list[str] = field(default_factory=list)
    context_level: int = 0
    requires_task_contract: bool = False
    confidence: float = 1.0
    reasoning_summary: str = ""
    unresolved_ambiguities: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        if self.context_level not in {0, 1, 2, 3}:
            raise ValueError(f"Context level must be in {{0, 1, 2, 3}}, got {self.context_level}")
