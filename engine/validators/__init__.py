from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of a single validator execution."""

    valid: bool
    validator_id: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
