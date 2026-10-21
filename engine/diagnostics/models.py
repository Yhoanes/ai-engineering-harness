from dataclasses import dataclass, field
from typing import Literal

DiagnosticStatus = Literal["PASS", "FAIL", "WARN", "SKIPPED"]


@dataclass
class DiagnosticCheck:
    id: str
    status: DiagnosticStatus
    message: str
    required: bool
    remediation: str | None = None


@dataclass
class DiagnosticReport:
    harness_version: str | None
    python_version: str
    environment: str
    checks: list[DiagnosticCheck] = field(default_factory=list)
    overall_status: Literal[
        "READY", "INSTALLATION_ERROR", "REQUIREMENT_MISSING", "CONFIGURATION_ERROR"
    ] = "CONFIGURATION_ERROR"
