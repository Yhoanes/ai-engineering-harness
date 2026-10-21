from __future__ import annotations

from engine.validators.validate_approval_gate import validate


def test_valid_approval(valid_standard_task: dict) -> None:
    result = validate(valid_standard_task)
    assert result.valid, f"Errors: {result.errors}"


def test_missing_approved_by(invalid_task_missing_approval: dict) -> None:
    result = validate(invalid_task_missing_approval)
    assert not result.valid
    assert any("approved_by" in e for e in result.errors)


def test_missing_approved_at(valid_standard_task: dict) -> None:
    valid_standard_task["approved_at"] = None
    result = validate(valid_standard_task)
    assert not result.valid
    assert any("approved_at" in e for e in result.errors)


def test_invalid_iso_format(valid_standard_task: dict) -> None:
    valid_standard_task["approved_at"] = "not-a-date"
    result = validate(valid_standard_task)
    assert not result.valid
    assert any("ISO 8601" in e for e in result.errors)


def test_pending_approval_fails(valid_standard_task: dict) -> None:
    valid_standard_task["approval_status"] = "pending"
    result = validate(valid_standard_task)
    assert not result.valid


def test_provenance_warning_when_missing(valid_standard_task: dict) -> None:
    valid_standard_task["approval_source"] = None
    result = validate(valid_standard_task)
    assert result.valid  # Not an error, just warning
    assert any("approval_source" in w for w in result.warnings)


def test_empty_string_approved_by(valid_standard_task: dict) -> None:
    valid_standard_task["approved_by"] = "   "
    result = validate(valid_standard_task)
    assert not result.valid
