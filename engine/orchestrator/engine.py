from pathlib import Path
from typing import Any

from core.context.metadata_paths import MetadataPaths
from engine.execution.models import (
    AccessMode,
    ExecutionCapabilities,
    ExecutionIsolation,
    ExecutionPurpose,
    ExecutionRequest,
    ExecutionResult,
    ScopedAccess,
)
from engine.execution.provider import ExecutionProvider
from engine.governance.authority import (
    get_execution_authority,
    load_authority_matrix,
    network_allows,
    path_allows,
    scope_allows,
    terminal_command_allows,
)
from engine.validators.validate_task_contract import validate


class HarnessEngine:
    def __init__(self, repo_root: Path, provider: ExecutionProvider | None = None):
        self.repo_root = repo_root.resolve()
        self.provider = provider
        self.paths = MetadataPaths(self.repo_root)

    def _load_task_contract(self, project_id: str, task_id: str) -> dict[str, Any]:
        import yaml
        contract_path = self.paths.task_contract(project_id, task_id)
        if not contract_path.is_file():
            raise ValueError(f"Task Contract not found: {project_id}/{task_id}")

        with contract_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        validation_result = validate(data)
        if not validation_result.valid:
            raise ValueError(f"Task Contract validation failed: {validation_result.errors}")  # noqa: E501

        return data

    def _parse_task_scope(self, task: dict[str, Any]) -> dict[str, Any]:
        scope = task.get("scope", {})
        planned = scope.get("planned_paths", {})
        actions = scope.get("allowed_actions", {})
        forbidden = scope.get("forbidden_actions", [])

        modify_raw = planned.get("modify", {})
        modify_mode = AccessMode(modify_raw.get("mode", "deny_all"))
        modify_values = frozenset(modify_raw.get("values", []))
        modify_access = ScopedAccess(mode=modify_mode, values=modify_values)

        read_raw = planned.get("read", {})
        read_mode = AccessMode(read_raw.get("mode", "deny_all"))
        read_values = frozenset(read_raw.get("values", []))
        read_access = ScopedAccess(mode=read_mode, values=read_values)

        terminal_raw = actions.get("terminal", {})
        terminal_mode = AccessMode(terminal_raw.get("mode", "deny_all"))
        terminal_values = frozenset(terminal_raw.get("values", []))
        terminal_access = ScopedAccess(mode=terminal_mode, values=terminal_values)
        terminal_allowed = terminal_mode != AccessMode.DENY_ALL

        network_allowed = actions.get("network_allowed", False)


        return {
            "modify_access": modify_access,
            "read_access": read_access,
            "terminal_allowed": terminal_allowed,
            "terminal_access": terminal_access,
            "network_allowed": network_allowed,
            "forbidden_actions": frozenset(forbidden)
        }

    def _validate_authority(self, task_scope: dict[str, Any], specialist: str) -> None:
        matrix = load_authority_matrix(self.repo_root)
        auth = get_execution_authority(matrix, specialist)

        if not scope_allows(auth.read_paths, task_scope["read_access"], path_allows):
            raise ValueError("Task read scope exceeds specialist authority.")

        if not scope_allows(auth.modify_paths, task_scope["modify_access"], path_allows):
            raise ValueError("Task modify scope exceeds specialist authority.")

        if not scope_allows(auth.terminal_commands, task_scope["terminal_access"], terminal_command_allows):  # noqa: E501
            raise ValueError("Task terminal scope exceeds specialist authority.")

        if not network_allows(auth.network_allowed, task_scope["network_allowed"]):
            raise ValueError("Task network scope exceeds specialist authority.")

    def run_task(self, project_id: str, task_id: str, intent: str) -> ExecutionResult:
        if self.provider is None:
            raise ValueError("ExecutionProvider is required for run_task")

        task = self._load_task_contract(project_id, task_id)

        assigned_workflow = task.get("assigned_workflow")
        if assigned_workflow != "implement-task":
            raise ValueError(f"Unsupported workflow: {assigned_workflow}")

        assigned_specialists = task.get("assigned_specialists", [])
        if not assigned_specialists:
            raise ValueError("Task has no assigned_specialists")
        specialist_role = assigned_specialists[0]

        task_scope = self._parse_task_scope(task)
        self._validate_authority(task_scope, specialist_role)

        capabilities = ExecutionCapabilities(
            terminal_allowed=task_scope["terminal_allowed"],
            terminal_allowed_commands=task_scope["terminal_access"],
            network_allowed=task_scope["network_allowed"],
            read_paths=task_scope["read_access"],
            modify_paths=task_scope["modify_access"],
            forbidden_actions=task_scope["forbidden_actions"]
        )

        from engine.context.models import ContextBundle
        context_bundle = ContextBundle(project=project_id, requested_level=0, loaded_level=0)

        request = ExecutionRequest(
            project_id=project_id,
            task_id=task_id,
            workspace_root=self.repo_root,
            intent=intent,
            purpose=ExecutionPurpose.IMPLEMENT,
            specialist_role=specialist_role,
            capabilities=capabilities,
            context_bundle=context_bundle,
            isolation=ExecutionIsolation(required=True)
        )

        return self.provider.execute(request)
