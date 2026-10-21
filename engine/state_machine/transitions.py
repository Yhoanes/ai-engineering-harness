from __future__ import annotations

from pathlib import Path

import yaml

# Valid status values
STATUS_VALUES = {
    "draft",
    "awaiting_approval",
    "approved",
    "in_progress",
    "blocked",
    "completed",
    "completed_with_deviation",
    "rejected",
}

TERMINAL_STATES = {"completed", "completed_with_deviation", "rejected"}

APPROVAL_STATUS_VALUES = {"pending", "approved", "rejected"}
ACCEPTANCE_STATUS_VALUES = {"pending", "passed", "passed_with_deviation", "failed"}

# Canonical transitions map
VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"awaiting_approval"},
    "awaiting_approval": {"approved", "rejected"},
    "approved": {"in_progress"},
    "in_progress": {"blocked", "completed", "completed_with_deviation", "rejected"},
    "blocked": {"in_progress"},
    "completed": set(),
    "completed_with_deviation": set(),
    "rejected": set(),
}


def is_valid_status(status: str) -> bool:
    return status in STATUS_VALUES


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATES


def is_valid_transition(from_status: str, to_status: str) -> bool:
    if from_status not in VALID_TRANSITIONS:
        return False
    return to_status in VALID_TRANSITIONS[from_status]


def get_valid_targets(from_status: str) -> set[str]:
    return VALID_TRANSITIONS.get(from_status, set())


def load_state_machine(path: Path | None = None) -> dict:
    if path is None:
        path = Path(__file__).parent.parent.parent / "core" / "schemas" / "state-machine.yaml"
    with path.open() as f:
        return yaml.safe_load(f)
