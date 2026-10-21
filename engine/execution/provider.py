from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from engine.execution.models import ExecutionRequest, ExecutionResult


@dataclass(frozen=True)
class ProviderCapabilities:
    terminal_execution: bool
    network_web: bool
    native_isolation: bool
    filesystem_mutation: bool
    long_running: bool


class ExecutionProvider(Protocol):
    def capabilities(self) -> ProviderCapabilities:
        """Return the capabilities of this provider."""
        ...

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute the request synchronously.
        This method will block until the execution reaches a terminal state.
        """
        ...
