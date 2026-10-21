# Validation Evidence for HARNESS-0028

## ARCHITECTURE
ExecutionRequest
-> AntigravityExecutionProvider
-> AutonomousRunner.run_execution()
-> LegacyExecutionOutcome
-> ExecutionResult

## PROVIDER
provider_id = antigravity

ProviderCapabilities:
terminal_execution=True
network_web=True
native_isolation=False
filesystem_mutation=True
long_running=False

native_isolation=False because WorktreeSandbox belongs to the Harness legacy wrapper, not to the intrinsic Antigravity/agy runtime.

## SUPPORT PROFILE
Fail-closed profile final.

SUPPORTED:
purpose == IMPLEMENT
terminal_allowed == True
terminal_allowed_commands.mode == UNRESTRICTED
network_allowed == True
read_paths.mode == UNRESTRICTED
forbidden_actions == empty
modify_paths: DENY_ALL, ALLOW_LIST, UNRESTRICTED
(with additional validation against legacy Task Contract).

REJECTED PRE-EXECUTION:
TEST
REVIEW
terminal disabled
restricted terminal commands
network disabled
restricted read paths
non-empty forbidden_actions

Unsupported requests fail before creating runner/executor/sandbox.

## MODIFY AUTHORITY
ExecutionRequest is the primary authority.

Each physical observed changed path must satisfy:
request_allowed(path) AND legacy_contract_allowed(path)

Legacy allowed paths semantics: literal membership.

ExecutionRequest.modify_paths:
- DENY_ALL -> ningún cambio permitido.
- ALLOW_LIST -> literal membership en request.values.
- UNRESTRICTED -> no restricción granular del request, pero legacy contract sigue limitando.

Renames: validate new path AND old path.
A violation produces: failure_kind = governance, ExecutionStatus.FAILED.
Does not affirm glob/prefix semantics.

## COMPLETION SEMANTICS
LegacyExecutionOutcome contains a structured signal: outcome_status

- Valid completion -> outcome_status == completed -> ExecutionStatus.COMPLETED
- Max steps exhausted without completion -> outcome_status == incomplete -> ExecutionStatus.INCOMPLETE
- Governance failure -> FAILED -> failure_kind=governance
- Runtime failure -> FAILED -> failure_kind=runtime

Does not use: no exception == completed.
Does not invent BLOCKED/CANCELLED.

## LEGACY EXECUTION OUTCOME
Forma real final: frozen.
Fields: trail (tuple), response, observed_changed_files (frozenset), failure_kind, outcome_status.
No last_response. No last_diff. No side-channel mutable.

## LEGACY COMPATIBILITY
AutonomousRunner.run(...) maintains the legacy contract: returns list[AuditTrailEntry].
New seam un_execution(...) returns LegacyExecutionOutcome.
No duplicate loop.
The existing legacy caller does not need to know the provider-neutral contract.

## CONTEXT BUNDLE
Because prepare_handoff() legacy internally loads context and engine/orchestrator is out of scope, HARNESS-0028 DOES NOT yet eliminate the legacy load.
Current behavior:
1. legacy prepare_handoff loads ContextBundle;
2. if ExecutionRequest already contains governed ContextBundle;
3. adapter replaces LOCALLY the handoff bundle via dataclasses.replace.

This preserves authority, DOES NOT modify global state, DOES NOT use monkeypatch, but causes a temporary redundant load. Documented as a legacy compatibility limitation. ContextLoader is NOT skipped.

## SPECIALIST
assigned_specialist provided -> uses assignment already resolved by Governance.
assigned_specialist None -> router legacy continues to function.
This is not a user-controlled override.

## TIMEOUT
Firma real legacy:
AntigravityCliExecutor(timeout: float = 630.0, dangerously_skip_permissions: bool = False)

ExecutionRequest.timeout_seconds adapts to:
AntigravityCliExecutor(timeout=float(...))

Semantics: timeout POR invocation of agy. NOT total deadline of run_execution.

## RESULT MAPPING
- reported_changed_files <- observed_changed_files
- output_text <- response.raw_text or ""
- execution_id <- conversation_id
- duration_seconds <- legacy metadata duration_seconds
- diagnostics.stderr:
  1. response.metadata["stderr"] when it exists;
  2. AuditTrailEntry.reason as fallback.

provider_metadata preserves when they exist: status, num_turns, usage, returncode, host_executor, conversation_id, duration_seconds, stderr.
Does not invent non-existent data.
