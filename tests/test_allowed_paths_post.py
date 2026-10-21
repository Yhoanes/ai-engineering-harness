from __future__ import annotations

from unittest.mock import patch

import pytest

from engine.validators.validate_allowed_paths_post import (
    _detect_all_changes,
    _resolve_safe_path,
    capture_baseline,
    validate,
)


def test_all_paths_within_scope(valid_standard_task: dict) -> None:
    actual = [
        "projects/analista/src/auth/login.py",
        "projects/analista/src/auth/jwt.py",
    ]
    result = validate(valid_standard_task, actual_paths=actual)
    assert result.valid, f"Errors: {result.errors}"


def test_path_outside_scope(valid_standard_task: dict) -> None:
    actual = [
        "projects/analista/src/auth/login.py",
        "projects/analista/config/database.yaml",  # Outside scope
    ]
    result = validate(valid_standard_task, actual_paths=actual)
    assert not result.valid
    assert any("outside of scope" in e for e in result.errors)


def test_task_contract_itself_excluded(valid_standard_task: dict) -> None:
    """The task contract file itself should be excluded from postcheck."""
    actual = [
        "projects/analista/src/auth/login.py",
        "projects/analista/tasks/TASK-0001.yaml",  # The task contract itself
    ]
    result = validate(valid_standard_task, actual_paths=actual)
    assert result.valid


def test_empty_actual_paths(valid_standard_task: dict) -> None:
    result = validate(valid_standard_task, actual_paths=[])
    assert result.valid  # No files modified is OK


def test_empty_scope_fails(valid_standard_task: dict) -> None:
    valid_standard_task["scope"]["planned_paths"]["modify"] = []
    result = validate(valid_standard_task, actual_paths=["some/file.py"])
    assert not result.valid


@patch("engine.validators.validate_allowed_paths_post._git_command")
@patch("engine.validators.validate_allowed_paths_post._calculate_sha256")
def test_capture_baseline_registers_untracked(mock_hash, mock_git, tmp_path):
    # AC-01: capture_baseline registra preexisting_untracked con path + sha256
    # AC-19: Orden del snapshot es determinista por path
    def git_side_effect(cmd, cwd):
        if "rev-parse" in cmd:
            return ["abcd123"]
        elif "status" in cmd:
            return []
        elif "ls-files" in cmd:
            return ["fileB.txt", "fileA.txt"]
        return []

    mock_git.side_effect = git_side_effect
    mock_hash.side_effect = lambda f, _: "a" * 64 if "A" in f else "b" * 64

    baseline = capture_baseline(tmp_path)

    assert "preexisting_untracked" in baseline
    untracked = baseline["preexisting_untracked"]
    assert len(untracked) == 2

    # Must be sorted by path
    assert untracked[0]["path"] == "fileA.txt"
    assert untracked[0]["sha256"] == "a" * 64
    assert untracked[1]["path"] == "fileB.txt"
    assert untracked[1]["sha256"] == "b" * 64


def test_resolve_safe_path_traversal(tmp_path):
    # AC-16: Path baseline inválido/path traversal -> FAIL/CANNOT_VALIDATE
    with pytest.raises(ValueError, match="Path traversal"):
        _resolve_safe_path("../outside.txt", tmp_path)

    with pytest.raises(ValueError, match="Path traversal"):
        _resolve_safe_path("/absolute/path", tmp_path)


@patch("engine.validators.validate_allowed_paths_post._git_command")
@patch("engine.validators.validate_allowed_paths_post._calculate_sha256")
def test_detect_all_changes_semantics(mock_hash, mock_git, valid_standard_task, tmp_path):
    mock_hash.return_value = "c" * 64

    # Baseline has preexisting untracked file 'preexisting.txt' with hash 'a'*64
    valid_standard_task["implementation_baseline"] = {
        "git_head": "abcd123",
        "preexisting_untracked": [
            {"path": "preexisting.txt", "sha256": "a" * 64},
            {"path": "modified_untracked.txt", "sha256": "b" * 64},
            {"path": "deleted_untracked.txt", "sha256": "c" * 64},
        ],
    }

    def git_side_effect(cmd, cwd):
        if "rev-parse" in cmd:
            return ["abcd123"]
        elif "diff" in cmd and "--cached" in cmd:
            return ["staged.txt"]
        elif "diff" in cmd and "abcd123..HEAD" in cmd:
            return ["committed.txt"]
        elif "diff" in cmd:
            return ["unstaged.txt"]
        elif "ls-files" in cmd:
            return [
                "preexisting.txt",  # kept same
                "modified_untracked.txt",  # hash changed
                "new_untracked.txt",  # new untracked
                # 'deleted_untracked.txt' is absent
            ]
        return []

    mock_git.side_effect = git_side_effect

    def hash_side_effect(path, cwd):
        if path == "preexisting.txt":
            return "a" * 64
        if path == "modified_untracked.txt":
            return "d" * 64  # changed
        if path == "new_untracked.txt":
            return "e" * 64
        return "0" * 64

    mock_hash.side_effect = hash_side_effect

    changes = _detect_all_changes(valid_standard_task, tmp_path)

    # AC-03: Nuevo untracked -> DETECTED
    assert "new_untracked.txt" in changes

    # AC-04: Preexisting untracked mismo hash -> IGNORED
    assert "preexisting.txt" not in changes

    # AC-05: Preexisting untracked distinto hash -> DETECTED
    assert "modified_untracked.txt" in changes

    # AC-06: Preexisting eliminado -> DETECTED
    assert "deleted_untracked.txt" in changes

    # AC-08: Staged -> DETECTED
    assert "staged.txt" in changes

    # AC-09: Unstaged -> DETECTED
    assert "unstaged.txt" in changes

    # AC-10: Committed -> DETECTED
    assert "committed.txt" in changes


@patch("engine.validators.validate_allowed_paths_post._git_command")
def test_detect_changes_legacy_baseline_no_untracked(mock_git, valid_standard_task, tmp_path):
    # AC-18: Baseline legacy sin snapshot + cero current untracked -> compatible
    valid_standard_task["implementation_baseline"] = {
        "git_head": "abcd123"
        # No preexisting_untracked
    }

    def git_side_effect(cmd, cwd):
        if "ls-files" in cmd:
            return []  # No current untracked
        return []

    mock_git.side_effect = git_side_effect

    changes = _detect_all_changes(valid_standard_task, tmp_path)
    assert not changes


@patch("engine.validators.validate_allowed_paths_post._git_command")
def test_detect_changes_legacy_baseline_with_untracked(mock_git, valid_standard_task, tmp_path):
    # AC-17: Baseline legacy sin snapshot + current untracked -> FAIL
    valid_standard_task["implementation_baseline"] = {"git_head": "abcd123"}

    def git_side_effect(cmd, cwd):
        if "ls-files" in cmd:
            return ["some_untracked.txt"]
        return []

    mock_git.side_effect = git_side_effect

    with pytest.raises(ValueError, match="Legacy baseline snapshot missing."):
        _detect_all_changes(valid_standard_task, tmp_path)


@patch("engine.validators.validate_allowed_paths_post._detect_all_changes")
def test_validate_exceptions_caught(mock_detect, valid_standard_task, tmp_path):
    # If detect raises ValueError, validate should return invalid ValidationResult
    mock_detect.side_effect = ValueError("Some error")
    result = validate(valid_standard_task, repo_root=tmp_path)
    assert not result.valid
    assert "Some error" in result.errors[0]


@patch("engine.validators.validate_allowed_paths_post._git_command")
def test_malformed_hashes_fail(mock_git, valid_standard_task, tmp_path):
    # AC-15: SHA-256 malformado -> FAIL
    valid_standard_task["implementation_baseline"] = {
        "git_head": "abcd123",
        "preexisting_untracked": [{"path": "file.txt", "sha256": "short"}],
    }

    def git_side_effect(cmd, cwd):
        if "ls-files" in cmd:
            return ["file.txt"]
        return []

    mock_git.side_effect = git_side_effect

    with pytest.raises(ValueError, match="Invalid SHA-256 hash"):
        _detect_all_changes(valid_standard_task, tmp_path)


@patch("engine.validators.validate_allowed_paths_post._git_command")
@patch("engine.validators.validate_allowed_paths_post._calculate_sha256")
def test_explicit_harness_0002_case(mock_hash, mock_git, valid_standard_task, tmp_path):
    harness_hash = "a" * 64
    valid_standard_task["implementation_baseline"] = {
        "git_head": "abcd123",
        "preexisting_untracked": [
            {"path": "projects/.harness-internal/tasks/HARNESS-0002.yaml", "sha256": harness_hash}
        ],
    }

    def git_side_effect(cmd, cwd):
        if "ls-files" in cmd:
            return ["projects/.harness-internal/tasks/HARNESS-0002.yaml"]
        return []

    mock_git.side_effect = git_side_effect

    # 1. Mismo contenido (mismo hash) -> IGNORE
    mock_hash.return_value = harness_hash
    changes_same = _detect_all_changes(valid_standard_task, tmp_path)
    assert "projects/.harness-internal/tasks/HARNESS-0002.yaml" not in changes_same

    # 2. Distinto contenido (distinto hash) -> DETECTED
    mock_hash.return_value = "b" * 64
    changes_diff = _detect_all_changes(valid_standard_task, tmp_path)
    assert "projects/.harness-internal/tasks/HARNESS-0002.yaml" in changes_diff
