import runpy
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from engine.validators import ValidationResult
from engine.validators.validate_task_contract import main, validate


@pytest.fixture
def valid_yaml_path(tmp_path):
    contract = {
        "project": "test",
        "task_id": "TASK-0001",
        "task_type": "standard",
        "title": "Test Task",
        "description": "Test task description",
        "status": "draft",
        "approval_status": "pending",
        "acceptance_status": "pending",
        "assigned_workflow": "implement-task",
        "assigned_specialists": ["harness-maintainer"],
        "evidence": {
            "validation_reports": [],
            "artifacts": []
        },
        "scope": {
            "planned_paths": {
                "modify": {"mode": "deny_all"},
                "read": {"mode": "unrestricted"}
            },
            "allowed_actions": {
                "terminal": {"mode": "deny_all"},
                "network_allowed": False
            }
        },
        "created_at": "2026-08-31T21:00:00Z"
    }
    p = tmp_path / "valid.yaml"
    with p.open("w", encoding="utf-8") as f:
        yaml.dump(contract, f)
    return str(p)


@pytest.fixture
def schema_invalid_yaml_path(tmp_path):
    contract = {
        "project": "test",
        "task_id": "TASK-0001",
        # missing required fields like title, status, etc.
    }
    p = tmp_path / "schema_invalid.yaml"
    with p.open("w", encoding="utf-8") as f:
        yaml.dump(contract, f)
    return str(p)


@pytest.fixture
def semantic_invalid_yaml_path(tmp_path):
    contract = {
        "project": "test",
        "task_id": "TASK-0001",
        "task_type": "standard",
        "title": "Test Task",
        "description": "Test task description",
        "status": "awaiting_approval",
        "approval_status": "approved", # approved but missing approved_by
        "acceptance_status": "pending",
        "assigned_workflow": "implement-task",
        "assigned_specialists": ["harness-maintainer"],
        "evidence": {
            "validation_reports": [],
            "artifacts": []
        },
        "scope": {
            "planned_paths": {
                "modify": {"mode": "deny_all"},
                "read": {"mode": "unrestricted"}
            },
            "allowed_actions": {
                "terminal": {"mode": "deny_all"},
                "network_allowed": False
            }
        },
        "created_at": "2026-08-31T21:00:00Z"
    }
    p = tmp_path / "semantic_invalid.yaml"
    with p.open("w", encoding="utf-8") as f:
        yaml.dump(contract, f)
    return str(p)


@pytest.fixture
def wrong_root_type_yaml_path(tmp_path):
    p = tmp_path / "wrong_type.yaml"
    with p.open("w", encoding="utf-8") as f:
        f.write("- item1\n- item2\n")
    return str(p)


@pytest.fixture
def malformed_yaml_path(tmp_path):
    p = tmp_path / "malformed.yaml"
    with p.open("w", encoding="utf-8") as f:
        f.write("key: \"unclosed string\n")
    return str(p)


def test_cli_pass(valid_yaml_path, capsys):
    assert main([valid_yaml_path]) == 0
    captured = capsys.readouterr()
    assert "Task Contract validation: PASS" in captured.out


def test_cli_fail_schema(schema_invalid_yaml_path, capsys):
    assert main([schema_invalid_yaml_path]) == 1
    captured = capsys.readouterr()
    assert "Task Contract validation: FAIL" in captured.out
    assert "Errors:" in captured.out
    assert "is a required property" in captured.out


def test_cli_fail_semantic(semantic_invalid_yaml_path, capsys):
    assert main([semantic_invalid_yaml_path]) == 1
    captured = capsys.readouterr()
    assert "Task Contract validation: FAIL" in captured.out
    assert "Errors:" in captured.out
    assert "approval_status is 'approved' but approved_by is missing" in captured.out


def test_cli_file_not_found(capsys):
    assert main(["nonexistent_fake_path.yaml"]) == 2
    captured = capsys.readouterr()
    assert "INPUT ERROR: File not found:" in captured.out


def test_cli_wrong_root_type(wrong_root_type_yaml_path, capsys):
    assert main([wrong_root_type_yaml_path]) == 2
    captured = capsys.readouterr()
    assert "INPUT ERROR: Task contract must be a YAML dictionary" in captured.out


def test_cli_malformed_yaml(malformed_yaml_path, capsys):
    assert main([malformed_yaml_path]) == 2
    captured = capsys.readouterr()
    assert "INPUT ERROR: Malformed YAML" in captured.out


def test_cli_internal_exception(valid_yaml_path):
    with patch("engine.validators.validate_task_contract.validate") as mock_validate:
        mock_validate.side_effect = RuntimeError("Something went wrong internally")
        with pytest.raises(RuntimeError):
            main([valid_yaml_path])


def test_executable_boundary_system_exit(valid_yaml_path):
    with patch("sys.argv", ["__main__.py", valid_yaml_path]):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("engine.validators.validate_task_contract", run_name="__main__")
        assert exc_info.value.code == 0


def test_programmatic_api_unchanged(valid_yaml_path):
    # Direct programmatic use of validate() should still return ValidationResult
    with Path(valid_yaml_path).open(encoding="utf-8") as f:
        task_data = yaml.safe_load(f)

    result = validate(task_data)
    assert isinstance(result, ValidationResult)
    assert result.valid is True
