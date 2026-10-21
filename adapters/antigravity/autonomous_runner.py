from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from engine.execution.models import AccessMode
from engine.validators.scope import normalize_access_scope

from .adapter import AntigravityAdapter
from .models import (
    AntigravityExecutor,
    AntigravityRequest,
    AntigravityResponse,
    AuditTrailEntry,
    LegacyExecutionOutcome,
)


# Workflows authorized for autonomous physical execution
class GovernanceViolationError(RuntimeError):
    pass


PLANNING_WORKFLOWS = frozenset({"plan-task"})
MUTATIONAL_WORKFLOWS = frozenset({"implement-task"})


class AutonomousRunner:
    def __init__(self, adapter: AntigravityAdapter, executor: AntigravityExecutor):
        self.adapter = adapter
        self.executor = executor

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _materialize_task_artifacts(self, sandbox_path: Path, request: AntigravityRequest) -> None:
        if not request.project:
            raise ValueError(f"Invalid project format: {request.project}")

        if not request.task_id:
            return

        candidates = [request.project]
        if request.project != ".harness-internal":
            candidates.append(".harness-internal")

        from core.context.metadata_paths import MetadataPaths

        paths = MetadataPaths(self.adapter.repo_root)

        for proj in candidates:
            try:
                task_file = paths.task_contract(proj, request.task_id)
                proposal_file = paths.proposal(proj, request.task_id)
            except ValueError as e:
                raise ValueError(str(e).replace("task", "task_id")) from e

            found_any = False
            if task_file.exists():
                found_any = True
                dest = sandbox_path / task_file.relative_to(self.adapter.repo_root)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(task_file, dest)

            if proposal_file.exists():
                found_any = True
                dest = sandbox_path / proposal_file.relative_to(self.adapter.repo_root)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(proposal_file, dest)

            if found_any:
                break

    def _save_audit_trail(self, project: str, task_id: str, trail: list[AuditTrailEntry]) -> None:
        if not task_id:
            return

        from core.context.metadata_paths import MetadataPaths

        paths = MetadataPaths(self.adapter.repo_root)

        try:
            audit_file = paths.audit_trail(project, task_id)
        except ValueError:
            return

        audit_file.parent.mkdir(parents=True, exist_ok=True)

        with audit_file.open("a", encoding="utf-8") as f:
            for entry in trail:
                d = {k: v for k, v in entry.__dict__.items() if v is not None}
                f.write(json.dumps(d) + "\n")

    def run(self, request: AntigravityRequest, max_steps: int = 5) -> list[AuditTrailEntry]:
        return list(self.run_execution(request, max_steps).trail)

    def run_execution(
        self, request: AntigravityRequest, max_steps: int = 5
    ) -> LegacyExecutionOutcome:
        trail: list[AuditTrailEntry] = []
        last_response: AntigravityResponse | None = None
        failure_kind: str | None = None
        outcome_status = "incomplete"
        observed_changed_files: set[str] = set()
        current_request = request

        for step in range(1, max_steps + 1):
            # 1. Planning / Routing
            try:
                # adapter.plan internally reloads the contract from disk
                plan = self.adapter.plan(current_request)
            except Exception as e:
                entry = AuditTrailEntry(
                    step=step,
                    status="failed",
                    reason=f"Planning failed: {e}",
                    timestamp=self._now(),
                )
                trail.append(entry)
                self._save_audit_trail(request.project, request.task_id or "", [entry])
                break

            wf = plan.route_decision.workflow_id
            spec = plan.route_decision.primary_specialist

            entry = AuditTrailEntry(
                step=step, status="planned", workflow=wf, specialist=spec, timestamp=self._now()
            )
            trail.append(entry)
            self._save_audit_trail(request.project, request.task_id or "", [entry])

            # 2. Check Human Gates before dispatch
            gate_triggered, gate_reason = self._check_gates(current_request, wf)
            if gate_triggered:
                entry = AuditTrailEntry(
                    step=step,
                    status="paused",
                    workflow=wf,
                    specialist=spec,
                    reason=gate_reason,
                    timestamp=self._now(),
                )
                trail.append(entry)
                self._save_audit_trail(request.project, request.task_id or "", [entry])
                break

            # 2b. Verify workflow is enabled for autonomous execution
            if wf not in PLANNING_WORKFLOWS and wf not in MUTATIONAL_WORKFLOWS:
                entry = AuditTrailEntry(
                    step=step,
                    status="paused",
                    workflow=wf,
                    specialist=spec,
                    reason=(f"Workflow '{wf}' is not enabled for autonomous physical execution."),
                    timestamp=self._now(),
                )
                trail.append(entry)
                self._save_audit_trail(request.project, request.task_id or "", [entry])
                break

            # 3. Dispatch / Execute
            from adapters.antigravity.cli_executor import AntigravityCliExecutor
            from engine.runner.sandbox import StagingSandbox, WorktreeSandbox

            try:
                if wf in PLANNING_WORKFLOWS:
                    sandbox = StagingSandbox(self.adapter.repo_root)
                elif wf in MUTATIONAL_WORKFLOWS:
                    sandbox = WorktreeSandbox(self.adapter.repo_root, baseline_commit="HEAD")
                    sandbox.setup()

                self._materialize_task_artifacts(sandbox.get_path(), current_request)

                entry = AuditTrailEntry(
                    step=step,
                    status="sandbox_created",
                    workflow=wf,
                    specialist=spec,
                    timestamp=self._now(),
                )
                trail.append(entry)
                self._save_audit_trail(request.project, request.task_id or "", [entry])

                host_exec = "agy_cli" if isinstance(self.executor, AntigravityCliExecutor) else None
                entry = AuditTrailEntry(
                    step=step,
                    status="dispatched",
                    workflow=wf,
                    specialist=spec,
                    host_executor=host_exec,
                    timestamp=self._now(),
                )
                trail.append(entry)
                self._save_audit_trail(request.project, request.task_id or "", [entry])

                try:
                    response = self.executor.execute(plan, sandbox_dir=sandbox.get_path())
                    last_response = response
                except Exception as e:
                    failure_kind = "runtime"
                    outcome_status = "failed"
                    entry = AuditTrailEntry(
                        step=step,
                        status="failed",
                        workflow=wf,
                        specialist=spec,
                        reason=f"Execution failed: {e}",
                        timestamp=self._now(),
                    )
                    trail.append(entry)
                    self._save_audit_trail(request.project, request.task_id or "", [entry])
                    break

                entry = AuditTrailEntry(
                    step=step,
                    status="executed",
                    workflow=wf,
                    specialist=spec,
                    host_executor=host_exec,
                    timestamp=self._now(),
                )
                trail.append(entry)
                self._save_audit_trail(request.project, request.task_id or "", [entry])

                diff_result = sandbox.get_diff()
                if not diff_result.success:
                    raise RuntimeError(diff_result.error)

                    # --- Scope validation ---
                contract = self.adapter._load_task_contract(request.project, request.task_id)
                raw_modify = []
                if contract:
                    raw_modify = (
                        contract.get("scope", {}).get("planned_paths", {}).get("modify", [])
                    )

                scoped_modify = normalize_access_scope(raw_modify)

                task_yaml_suffix = (
                    f"{current_request.task_id}.yaml" if current_request.task_id else None
                )
                proposal_md_suffix = (
                    f"{current_request.task_id}.md" if current_request.task_id else None
                )

                # Filter changes: exclude injected task contract YAML and proposal MD
                actual_changes = [
                    c
                    for c in diff_result.changes
                    if not (
                        (task_yaml_suffix and c.path.endswith(task_yaml_suffix))
                        or (proposal_md_suffix and c.path.endswith(proposal_md_suffix))
                    )
                ]

                for c in actual_changes:
                    if c.path:
                        observed_changed_files.add(c.path)
                    if getattr(c, "old_path", None):
                        observed_changed_files.add(c.old_path)

                # Collect all paths that must be in scope
                out_of_scope = []
                for c in actual_changes:
                    if c.path:
                        legacy_allowed = True
                        req_allowed = True

                        if scoped_modify.mode == AccessMode.DENY_ALL or (
                            scoped_modify.mode == AccessMode.ALLOW_LIST
                            and c.path not in scoped_modify.values
                        ):
                            legacy_allowed = False
                        # If UNRESTRICTED, legacy_allowed stays True

                        if current_request.modify_paths_mode:
                            if current_request.modify_paths_mode == AccessMode.DENY_ALL:
                                req_allowed = False
                            elif current_request.modify_paths_mode == AccessMode.ALLOW_LIST:
                                req_vals = current_request.modify_paths_values or frozenset()
                                if c.path not in req_vals:
                                    req_allowed = False

                        if not legacy_allowed or not req_allowed:
                            out_of_scope.append(c.path)

                    if getattr(c, "old_path", None):
                        legacy_allowed = True
                        req_allowed = True

                        if scoped_modify.mode == AccessMode.DENY_ALL or (
                            scoped_modify.mode == AccessMode.ALLOW_LIST
                            and c.old_path not in scoped_modify.values
                        ):
                            legacy_allowed = False

                        if current_request.modify_paths_mode:
                            if current_request.modify_paths_mode == AccessMode.DENY_ALL:
                                req_allowed = False
                            elif current_request.modify_paths_mode == AccessMode.ALLOW_LIST:
                                req_vals = current_request.modify_paths_values or frozenset()
                                if c.old_path not in req_vals:
                                    req_allowed = False

                        if not legacy_allowed or not req_allowed:
                            out_of_scope.append(c.old_path)

                if out_of_scope:
                    # Deduplicate while preserving order
                    seen = set()
                    dedup = [x for x in out_of_scope if not (x in seen or seen.add(x))]
                    raise GovernanceViolationError(f"Out-of-scope files: {dedup}")

                # Empty diff when modifications expected
                if (
                    wf == "implement-task"
                    and scoped_modify.mode == AccessMode.ALLOW_LIST
                    and not actual_changes
                ):
                    raise RuntimeError(
                        f"Empty diff: expected modifications to {scoped_modify.values}"
                    )

                # Validated changes = those within scope
                validated_changes = []
                for c in actual_changes:
                    is_valid = True
                    if scoped_modify.mode == AccessMode.DENY_ALL or (
                        scoped_modify.mode == AccessMode.ALLOW_LIST
                        and c.path not in scoped_modify.values
                    ):
                        is_valid = False

                    if is_valid:
                        validated_changes.append(c)

                entry = AuditTrailEntry(
                    step=step,
                    status="validated",
                    workflow=wf,
                    specialist=spec,
                    host_executor=host_exec,
                    timestamp=self._now(),
                )
                trail.append(entry)
                self._save_audit_trail(request.project, request.task_id or "", [entry])

                apply_result = sandbox.apply_to_main(validated_changes)
                if not apply_result.success:
                    raise RuntimeError(apply_result.error)

                entry = AuditTrailEntry(
                    step=step,
                    status="applied",
                    workflow=wf,
                    specialist=spec,
                    host_executor=host_exec,
                    timestamp=self._now(),
                )
                trail.append(entry)
                self._save_audit_trail(request.project, request.task_id or "", [entry])

            except GovernanceViolationError as e:
                failure_kind = "governance"
                outcome_status = "failed"
                entry = AuditTrailEntry(
                    step=step,
                    status="failed",
                    workflow=wf,
                    specialist=spec,
                    reason=f"Sandbox failed: {e}",
                    timestamp=self._now(),
                )
                trail.append(entry)
                self._save_audit_trail(request.project, request.task_id or "", [entry])
                break
            except Exception as e:
                failure_kind = "runtime"
                outcome_status = "failed"
                entry = AuditTrailEntry(
                    step=step,
                    status="failed",
                    workflow=wf,
                    specialist=spec,
                    reason=f"Sandbox failed: {e}",
                    timestamp=self._now(),
                )
                trail.append(entry)
                self._save_audit_trail(request.project, request.task_id or "", [entry])
                break
                break
            finally:
                if "sandbox" in locals():
                    sandbox.cleanup()

            # Exit after successful mutational implementation
            if wf in MUTATIONAL_WORKFLOWS:
                outcome_status = "completed"
                entry = AuditTrailEntry(
                    step=step,
                    status="paused",
                    workflow=wf,
                    specialist=spec,
                    reason=("Implementation applied. Awaiting governed review."),
                    timestamp=self._now(),
                )
                trail.append(entry)
                self._save_audit_trail(request.project, request.task_id or "", [entry])
                break

            # If it's a final state or closure, we mark completed
            if wf == "close-task":
                outcome_status = "completed"
                entry = AuditTrailEntry(
                    step=step,
                    status="completed",
                    workflow=wf,
                    specialist=spec,
                    timestamp=self._now(),
                )
                trail.append(entry)
                self._save_audit_trail(request.project, request.task_id or "", [entry])
                break

            # Automatically feed intent to next loop iteration
            from dataclasses import replace

            current_request = replace(
                current_request, user_input="Continue to next step based on updated state."
            )

        else:
            # Reached max_steps
            entry = AuditTrailEntry(
                step=max_steps + 1,
                status="paused",
                reason=f"max_steps ({max_steps}) reached.",
                timestamp=self._now(),
            )
            trail.append(entry)
            self._save_audit_trail(request.project, request.task_id or "", [entry])

        return LegacyExecutionOutcome(
            trail=tuple(trail),
            response=last_response,
            observed_changed_files=frozenset(observed_changed_files),
            failure_kind=failure_kind,
            outcome_status=outcome_status,
        )

    def _check_gates(
        self, request: AntigravityRequest, workflow_id: str
    ) -> tuple[bool, str | None]:
        if not request.task_id:
            return False, None

        # We must load the latest contract from disk to check gates
        contract = self.adapter._load_task_contract(request.project, request.task_id)
        if not contract:
            return False, None

        status = contract.get("status")
        approval_status = contract.get("approval_status")
        acceptance_status = contract.get("acceptance_status")

        if status == "awaiting_approval":
            return True, "Human Gate: Task is awaiting_approval."
        if approval_status == "pending":
            return True, "Human Gate: approval_status is pending."
        if status in ("completed", "completed_with_deviation") and acceptance_status == "pending":
            return True, "Human Gate: Task acceptance is pending."

        # Escalation gate from routing
        if workflow_id == "discuss" and "Escalation" in getattr(request, "user_input", ""):
            return True, "Human Gate: Escalation required."

        return False, None
