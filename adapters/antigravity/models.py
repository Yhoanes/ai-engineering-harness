from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from engine.context.models import ContextBundle
from engine.execution.models import AccessMode
from engine.orchestrator.models import OrchestratorHandoff
from engine.router.models import RouteDecision


@dataclass(frozen=True)
class AntigravityRequest:
    project: str
    user_input: str
    task_id: str | None = None
    requested_workflow: str | None = None
    existing_task_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    conversation_context: str | None = None

    # Provider-neutral seams
    context_bundle: ContextBundle | None = None
    assigned_specialist: str | None = None
    modify_paths_mode: AccessMode | None = None
    modify_paths_values: frozenset[str] | None = None


@dataclass(frozen=True)
class AntigravityExecutionPlan:
    route_decision: RouteDecision
    orchestrator_handoff: OrchestratorHandoff
    specialist_prompt: str
    workflow_prompt: str
    context_payload: str
    restrictions: list[str]
    expected_output_contract: list[str]
    final_prompt: str


@dataclass(frozen=True)
class AntigravityResponse:
    raw_text: str
    structured_output: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LegacyExecutionOutcome:
    trail: tuple[AuditTrailEntry, ...]
    response: AntigravityResponse | None
    observed_changed_files: frozenset[str]
    failure_kind: str | None = None
    outcome_status: str = "incomplete"


@dataclass(frozen=True)
class AntigravityResult:
    status: str
    workflow: str
    specialist: str
    output: AntigravityResponse
    warnings: list[str] = field(default_factory=list)
    next_action: str = ""


@dataclass(frozen=True)
class AuditTrailEntry:
    step: int
    # planned, sandbox_created, dispatched, executed, validated, applied,
    # paused, failed, completed
    status: str
    workflow: str | None = None
    specialist: str | None = None
    host_executor: str | None = None
    reason: str | None = None
    timestamp: str | None = None


class AntigravityExecutor(Protocol):
    def execute(self, plan: AntigravityExecutionPlan, sandbox_dir: Path) -> AntigravityResponse: ...
