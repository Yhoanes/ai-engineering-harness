from __future__ import annotations

import types
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from engine.context.models import ContextBundle


class ExecutionPurpose(Enum):
    IMPLEMENT = "implement"
    TEST = "test"
    REVIEW = "review"


class ExecutionStatus(Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    INCOMPLETE = "incomplete"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ExecutionIsolation:
    required: bool


class AccessMode(Enum):
    DENY_ALL = "deny_all"
    ALLOW_LIST = "allow_list"
    UNRESTRICTED = "unrestricted"


@dataclass(frozen=True)
class ScopedAccess:
    mode: AccessMode
    values: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self):
        if self.mode in (AccessMode.DENY_ALL, AccessMode.UNRESTRICTED) and self.values:
            raise ValueError(f"values must be empty when mode is {self.mode.name}")
        if self.mode == AccessMode.ALLOW_LIST and not self.values:
            raise ValueError(
                "values cannot be empty when mode is ALLOW_LIST. Use DENY_ALL instead."
            )


@dataclass(frozen=True)
class ExecutionCapabilities:
    terminal_allowed: bool
    terminal_allowed_commands: ScopedAccess
    network_allowed: bool
    read_paths: ScopedAccess
    modify_paths: ScopedAccess
    forbidden_actions: frozenset[str]

    def __post_init__(self):
        if not self.terminal_allowed and self.terminal_allowed_commands.mode != AccessMode.DENY_ALL:
            raise ValueError(
                "If terminal_allowed is False, terminal_allowed_commands MUST be DENY_ALL."
            )


@dataclass(frozen=True)
class ExecutionDiagnostics:
    stdout: str | None = None
    stderr: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ExecutionRequest:
    project_id: str
    task_id: str
    workspace_root: Path
    intent: str
    purpose: ExecutionPurpose
    specialist_role: str
    capabilities: ExecutionCapabilities
    context_bundle: ContextBundle
    isolation: ExecutionIsolation
    timeout_seconds: int | None = None

    def __post_init__(self):
        if not self.project_id:
            raise ValueError("project_id cannot be empty")
        if not self.task_id:
            raise ValueError("task_id cannot be empty")
        if not self.intent:
            raise ValueError("intent cannot be empty")
        if not self.specialist_role:
            raise ValueError("specialist_role cannot be empty")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive or None")


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    provider_id: str
    reported_changed_files: frozenset[str]
    output_text: str
    diagnostics: ExecutionDiagnostics
    execution_id: str | None = None
    duration_seconds: float | None = None
    provider_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.provider_id:
            raise ValueError("provider_id cannot be empty")
        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative or None")

        # Defensive shallow copy exposed through a read-only MappingProxyType;
        # nested provider-specific values are not deep-frozen.
        if not isinstance(self.provider_metadata, types.MappingProxyType):
            object.__setattr__(
                self,
                "provider_metadata",
                types.MappingProxyType(dict(self.provider_metadata))
            )
