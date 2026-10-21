from __future__ import annotations

from engine.validators.validate_acceptance_gate import validate


def test_valid_acceptance() -> None:
    task = {
        "acceptance_status": "passed",
        "accepted_by": "Yhoanes",
        "accepted_at": "2026-08-28T16:00:00-04:00",
    }
    result = validate(task)
    assert result.valid, f"Errors: {result.errors}"


def test_valid_acceptance_with_deviation() -> None:
    task = {
        "acceptance_status": "passed_with_deviation",
        "accepted_by": "Yhoanes",
        "accepted_at": "2026-08-28T16:00:00-04:00",
    }
    result = validate(task)
    assert result.valid


def test_pending_acceptance_fails() -> None:
    task = {
        "acceptance_status": "pending",
        "accepted_by": None,
        "accepted_at": None,
    }
    result = validate(task)
    assert not result.valid


def test_failed_acceptance_fails() -> None:
    task = {
        "acceptance_status": "failed",
        "accepted_by": "Yhoanes",
        "accepted_at": "2026-08-28T16:00:00-04:00",
    }
    result = validate(task)
    assert not result.valid


def test_missing_accepted_by() -> None:
    task = {
        "acceptance_status": "passed",
        "accepted_by": None,
        "accepted_at": "2026-08-28T16:00:00-04:00",
    }
    result = validate(task)
    assert not result.valid
    assert any("accepted_by" in e for e in result.errors)


def test_invalid_iso_accepted_at() -> None:
    task = {
        "acceptance_status": "passed",
        "accepted_by": "Yhoanes",
        "accepted_at": "yesterday",
    }
    result = validate(task)
    assert not result.valid
    assert any("ISO 8601" in e for e in result.errors)
