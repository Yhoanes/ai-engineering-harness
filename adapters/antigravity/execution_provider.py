
from engine.execution.models import (
    AccessMode,
    ExecutionDiagnostics,
    ExecutionPurpose,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from engine.execution.provider import ExecutionProvider, ProviderCapabilities

from .adapter import AntigravityAdapter
from .autonomous_runner import AutonomousRunner
from .cli_executor import AntigravityCliExecutor
from .models import AntigravityRequest


class AntigravityExecutionProvider(ExecutionProvider):
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            terminal_execution=True,
            network_web=True,
            native_isolation=False,
            filesystem_mutation=True,
            long_running=False,
        )

    def _validate_supported_request(self, request: ExecutionRequest) -> None:
        if request.purpose != ExecutionPurpose.IMPLEMENT:
            raise ValueError(f"ExecutionPurpose {request.purpose} is not supported by legacy wrapper.")  # noqa: E501

        caps = request.capabilities
        if not caps.terminal_allowed:
            raise ValueError("Antigravity requires terminal access (terminal_allowed=True).")

        if caps.terminal_allowed_commands.mode != AccessMode.UNRESTRICTED:
            raise ValueError("Antigravity requires UNRESTRICTED terminal_allowed_commands.")

        if not caps.network_allowed:
            raise ValueError("Antigravity requires network_allowed=True.")

        if caps.read_paths.mode != AccessMode.UNRESTRICTED:
            raise ValueError("Antigravity requires UNRESTRICTED read_paths.")

        if caps.forbidden_actions:
            raise ValueError("Antigravity cannot authoritatively enforce non-empty forbidden_actions.")  # noqa: E501

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self._validate_supported_request(request)

        legacy_request = AntigravityRequest(
            project=request.project_id,
            user_input=request.intent,
            task_id=request.task_id,
            context_bundle=request.context_bundle,
            assigned_specialist=request.specialist_role,
            requested_workflow="implement-task" if request.purpose == ExecutionPurpose.IMPLEMENT else None,  # noqa: E501
            modify_paths_mode=request.capabilities.modify_paths.mode,
            modify_paths_values=request.capabilities.modify_paths.values,
        )

        adapter = AntigravityAdapter(request.workspace_root)

        # Determine timeout. Default for CLI executor is 630.0.
        # request.timeout_seconds applies to the *per-call* timeout in the legacy model.
        timeout = float(request.timeout_seconds) if request.timeout_seconds else 630.0

        # Instantiate executor and runner
        # Note: dangerously_skip_permissions is enabled strictly because
        # _validate_supported_request() guarantees the request has
        # UNRESTRICTED terminal_commands and terminal_allowed=True.
        # This runtime flag does not replace or broaden Harness authority.
        executor = AntigravityCliExecutor(
            timeout=timeout,
            dangerously_skip_permissions=True
        )
        runner = AutonomousRunner(adapter, executor)

        # Execute
        try:
            # We assume a fixed max_steps of 5 for legacy mutational workflows.
            outcome = runner.run_execution(legacy_request, max_steps=5)
        except Exception as e:
            diagnostics = ExecutionDiagnostics(stderr=str(e))
            provider_metadata = {"failure_kind": "runtime"}
            return ExecutionResult(
                provider_id="antigravity",
                status=ExecutionStatus.FAILED,
                reported_changed_files=frozenset(),
                output_text="",
                execution_id=None,
                duration_seconds=None,
                diagnostics=diagnostics,
                provider_metadata=provider_metadata,
            )

        # Mapping outcome back to ExecutionResult
        # If the runner completes without raising an exception, it successfully executed the loop.
        # But wait, did it apply anything? We can look at trail to see if it completed successfully.

        if outcome.failure_kind:
            meta = dict(outcome.response.metadata) if outcome.response and outcome.response.metadata else {}  # noqa: E501

            stderr_val = meta.get("stderr")
            if not stderr_val and outcome.trail and outcome.trail[-1].reason:
                stderr_val = outcome.trail[-1].reason

            diagnostics = ExecutionDiagnostics(stderr=stderr_val)
            meta["failure_kind"] = outcome.failure_kind
            return ExecutionResult(
                provider_id="antigravity",
                status=ExecutionStatus.FAILED,
                reported_changed_files=outcome.observed_changed_files,
                output_text=(outcome.response.raw_text if outcome.response else "") or "",
                execution_id=meta.get("conversation_id"),
                duration_seconds=float(meta["duration_seconds"]) if "duration_seconds" in meta else None,  # noqa: E501
                diagnostics=diagnostics,
                provider_metadata=meta,
            )

        # Success mapping
        output_text = (outcome.response.raw_text if outcome.response else "") or ""

        conversation_id = None
        duration_seconds = None
        provider_metadata = {}

        if outcome.response and outcome.response.metadata:
            meta = outcome.response.metadata
            conversation_id = meta.get("conversation_id")
            if "duration_seconds" in meta:
                import contextlib
                with contextlib.suppress(ValueError, TypeError):
                    duration_seconds = float(meta["duration_seconds"])
            # Propagate other legacy metadata
            provider_metadata = dict(meta)

        return ExecutionResult(
            provider_id="antigravity",
            status=ExecutionStatus.COMPLETED if outcome.outcome_status == 'completed' else ExecutionStatus.INCOMPLETE,  # noqa: E501
            reported_changed_files=outcome.observed_changed_files,
            output_text=output_text,
            execution_id=conversation_id,
            duration_seconds=duration_seconds,
            diagnostics=ExecutionDiagnostics(stderr=provider_metadata.get("stderr")),
            provider_metadata=provider_metadata,
        )
