from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.orchestrator.orchestrator import prepare_handoff
from engine.router.router import route_request

from .models import (
    AntigravityExecutionPlan,
    AntigravityExecutor,
    AntigravityRequest,
    AntigravityResult,
)
from .prompt_builder import build_prompt
from .response_parser import parse_response


class AntigravityAdapter:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()

    def _normalize_request(self, request: AntigravityRequest) -> AntigravityRequest:
        if not request.project:
            raise ValueError("project is required")
        if not request.user_input.strip():
            raise ValueError("user_input cannot be empty")

        from core.context.metadata_paths import is_valid_project_id, is_valid_task_id

        if not is_valid_project_id(request.project):
            raise ValueError("Invalid project format")

        if request.task_id is not None:
            if not isinstance(request.task_id, str):
                raise ValueError("task_id must be a string")
            if not request.task_id.strip():
                raise ValueError("task_id cannot be empty string")
            if not is_valid_task_id(request.task_id):
                raise ValueError("Invalid task_id format")

        return request

    def _load_task_contract(self, project: str, task_id: str) -> dict[str, Any] | None:
        import yaml

        from core.context.metadata_paths import MetadataPaths

        paths = MetadataPaths(self.repo_root)
        try:
            contract_path = paths.task_contract(project, task_id)
        except ValueError:
            return None

        if contract_path.is_file():
            try:
                with contract_path.open(encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except Exception:
                pass

        return None

    def plan(self, request: AntigravityRequest) -> AntigravityExecutionPlan:
        request = self._normalize_request(request)

        task_contract = None
        if request.task_id:
            task_contract = self._load_task_contract(request.project, request.task_id)

        # 1. Routing
        if request.requested_workflow and request.assigned_specialist:
            from engine.router.models import RouteDecision
            decision = RouteDecision(
                workflow_id=request.requested_workflow,
                primary_specialist=request.assigned_specialist,
                # Compatibility metadata required by downstream processing, not new authority decisions.  # noqa: E501
                context_level=2,
                requires_task_contract=True,
                reasoning_summary="Governed request bypasses router.",
            )
        else:
            decision = route_request(request.user_input, task_contract, self.repo_root)

            if request.assigned_specialist:
                from dataclasses import replace
                decision = replace(decision, primary_specialist=request.assigned_specialist)

        # 2. Orchestrator
        handoff = prepare_handoff(
            decision=decision,
            project_key=request.project,
            repo_root=self.repo_root,
            existing_task_ids=request.existing_task_ids,
            task_id=request.task_id,
            existing_contract=task_contract,
        )

        if request.context_bundle:
            from dataclasses import replace
            # Note: prepare_handoff unconditionally invokes load_context.
            # We explicitly override the loaded bundle here with the one provided in the request
            # to preserve governance authority, accepting the duplicate load overhead.
            handoff = replace(handoff, context_bundle=request.context_bundle)

        # 3. Prompt Building
        prompt_data = build_prompt(
            repo_root=self.repo_root,
            handoff=handoff,
            user_input=request.user_input,
            conversation_context=request.conversation_context,
        )

        return AntigravityExecutionPlan(
            route_decision=decision,
            orchestrator_handoff=handoff,
            specialist_prompt=prompt_data["specialist_prompt"],  # type: ignore
            workflow_prompt=prompt_data["workflow_prompt"],  # type: ignore
            context_payload=prompt_data["context_payload"],  # type: ignore
            restrictions=handoff.restrictions,
            expected_output_contract=prompt_data["expected_output_contract"],  # type: ignore
            final_prompt=prompt_data["final_prompt"],  # type: ignore
        )

    def execute(
        self, request: AntigravityRequest, executor: AntigravityExecutor
    ) -> AntigravityResult:
        if executor is None:
            raise ValueError("executor is explicitly required for EXECUTE mode")

        plan = self.plan(request)
        response = executor.execute(plan)

        parsed_response = parse_response(response.raw_text)

        warnings = list(parsed_response.metadata.get("warnings", []))
        if (
            request.requested_workflow
            and request.requested_workflow != plan.route_decision.workflow_id
        ):
            warnings.append(
                f"requested_workflow '{request.requested_workflow}' was ignored by Router."
            )

        return AntigravityResult(
            status="success",
            workflow=plan.route_decision.workflow_id,
            specialist=plan.route_decision.primary_specialist,
            output=parsed_response,
            warnings=warnings,
            next_action=plan.orchestrator_handoff.next_action,
        )
