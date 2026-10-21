from __future__ import annotations

import pytest

from engine.state_machine.transitions import (
    STATUS_VALUES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    get_valid_targets,
    is_terminal,
    is_valid_transition,
)
from engine.validators.validate_transition import validate


class TestStateMachineConstants:
    def test_all_status_values_present(self) -> None:
        expected = {
            "draft",
            "awaiting_approval",
            "approved",
            "in_progress",
            "blocked",
            "completed",
            "completed_with_deviation",
            "rejected",
        }
        assert expected == STATUS_VALUES

    def test_terminal_states(self) -> None:
        assert {"completed", "completed_with_deviation", "rejected"} == TERMINAL_STATES

    def test_all_statuses_have_transition_entry(self) -> None:
        for status in STATUS_VALUES:
            assert status in VALID_TRANSITIONS


class TestValidTransitions:
    @pytest.mark.parametrize(
        "from_s,to_s",
        [
            ("draft", "awaiting_approval"),
            ("awaiting_approval", "approved"),
            ("awaiting_approval", "rejected"),
            ("approved", "in_progress"),
            ("in_progress", "blocked"),
            ("in_progress", "completed"),
            ("in_progress", "completed_with_deviation"),
            ("in_progress", "rejected"),
            ("blocked", "in_progress"),
        ],
    )
    def test_valid_transition(self, from_s: str, to_s: str) -> None:
        assert is_valid_transition(from_s, to_s)
        result = validate(from_s, to_s)
        assert result.valid, f"Expected valid: {from_s} -> {to_s}, errors: {result.errors}"


class TestInvalidTransitions:
    @pytest.mark.parametrize(
        "from_s,to_s",
        [
            ("draft", "approved"),
            ("draft", "in_progress"),
            ("draft", "completed"),
            ("awaiting_approval", "in_progress"),
            ("awaiting_approval", "draft"),
            ("approved", "draft"),
            ("approved", "completed"),
            ("in_progress", "draft"),
            ("in_progress", "approved"),
            ("blocked", "completed"),
            ("blocked", "draft"),
        ],
    )
    def test_invalid_transition(self, from_s: str, to_s: str) -> None:
        assert not is_valid_transition(from_s, to_s)
        result = validate(from_s, to_s)
        assert not result.valid


class TestTerminalStates:
    @pytest.mark.parametrize("terminal", ["completed", "completed_with_deviation", "rejected"])
    def test_terminal_has_no_targets(self, terminal: str) -> None:
        assert get_valid_targets(terminal) == set()
        assert is_terminal(terminal)

    @pytest.mark.parametrize("terminal", ["completed", "completed_with_deviation", "rejected"])
    def test_cannot_transition_from_terminal(self, terminal: str) -> None:
        for target in STATUS_VALUES:
            result = validate(terminal, target)
            assert not result.valid, f"Should block {terminal} -> {target}"

    def test_rejected_is_terminal(self) -> None:
        """Rejected is terminal — no transition from rejected to any state."""
        assert is_terminal("rejected")
        assert get_valid_targets("rejected") == set()
        # Explicitly: rejected -> draft does NOT exist
        assert not is_valid_transition("rejected", "draft")
        result = validate("rejected", "draft")
        assert not result.valid


class TestEdgeCases:
    def test_invalid_source_status(self) -> None:
        result = validate("nonexistent", "draft")
        assert not result.valid

    def test_invalid_target_status(self) -> None:
        result = validate("draft", "nonexistent")
        assert not result.valid

    def test_same_status_transition(self) -> None:
        result = validate("draft", "draft")
        assert not result.valid
