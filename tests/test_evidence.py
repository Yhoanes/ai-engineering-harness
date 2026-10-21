from __future__ import annotations

from engine.validators.validate_evidence import validate


def test_valid_evidence_all_present() -> None:
    task = {
        "task_type": "standard",
        "evidence": {
            "tests": {"status": "passed", "skip_reason": None},
            "code_review": {"status": "approved", "skip_reason": None},
            "security_review": {"status": "passed", "skip_reason": None},
        },
    }
    result = validate(task)
    assert result.valid, f"Errors: {result.errors}"


def test_skipped_without_reason_fails(
    invalid_task_skip_no_reason: dict,
) -> None:
    result = validate(invalid_task_skip_no_reason)
    assert not result.valid
    assert any("skip_reason" in e for e in result.errors)


def test_skipped_with_reason_light_task(valid_light_task: dict) -> None:
    result = validate(valid_light_task)
    assert result.valid, f"Errors: {result.errors}"


def test_standard_task_cannot_skip_tests() -> None:
    task = {
        "task_type": "standard",
        "evidence": {
            "tests": {
                "status": "skipped",
                "skip_reason": "I dont want to test",
            },
            "code_review": {"status": "approved", "skip_reason": None},
            "security_review": {"status": "passed", "skip_reason": None},
        },
    }
    result = validate(task)
    assert not result.valid
    assert any("cannot be skipped" in e for e in result.errors)


def test_standard_task_cannot_skip_code_review() -> None:
    task = {
        "task_type": "standard",
        "evidence": {
            "tests": {"status": "passed", "skip_reason": None},
            "code_review": {
                "status": "skipped",
                "skip_reason": "No time",
            },
            "security_review": {"status": "passed", "skip_reason": None},
        },
    }
    result = validate(task)
    assert not result.valid
    assert any("cannot be skipped" in e for e in result.errors)


def test_null_evidence_warns() -> None:
    task = {
        "task_type": "standard",
        "evidence": {
            "tests": {"status": None},
            "code_review": {"status": None},
            "security_review": {"status": None},
        },
    }
    result = validate(task)
    assert result.valid  # Warnings only for null
    assert len(result.warnings) > 0


def test_failed_evidence_warns() -> None:
    task = {
        "task_type": "standard",
        "evidence": {
            "tests": {"status": "failed", "skip_reason": None},
            "code_review": {"status": "approved", "skip_reason": None},
            "security_review": {"status": "passed", "skip_reason": None},
        },
    }
    result = validate(task)
    assert result.valid  # Warning, not blocking
    assert any("failed" in w for w in result.warnings)


# ─── Bootstrap exception tests ───


# Policy fixture matching core/policies/bootstrap-exception.yaml structure
_BOOTSTRAP_POLICY = {
    "exception": {
        "id": "HARNESS-BOOTSTRAP-0001",
        "type": "bootstrap",
        "authorized_skips": {
            "security_review": {"status": "skipped", "reason": "bootstrap"},
            "code_review": {"status": "skipped", "reason": "bootstrap"},
        },
    },
}

# Policy WITHOUT code_review authorized
_BOOTSTRAP_POLICY_NO_CODE_REVIEW = {
    "exception": {
        "id": "HARNESS-BOOTSTRAP-0001",
        "type": "bootstrap",
        "authorized_skips": {
            "security_review": {"status": "skipped", "reason": "bootstrap"},
        },
    },
}


def test_standard_task_normal_code_review_skipped_fails() -> None:
    """Standard task (non-bootstrap) cannot skip code_review, even with policy."""
    task = {
        "task_id": "TASK-0099",
        "task_type": "standard",
        "evidence": {
            "tests": {"status": "passed", "skip_reason": None},
            "code_review": {"status": "skipped", "skip_reason": "No reviewer available"},
            "security_review": {"status": "passed", "skip_reason": None},
        },
    }
    result = validate(task, bootstrap_policy=_BOOTSTRAP_POLICY)
    assert not result.valid
    assert any("cannot be skipped" in e for e in result.errors)


def test_bootstrap_task_with_policy_code_review_passes() -> None:
    """HARNESS-BOOTSTRAP-0001 + policy authorizes code_review skip → PASS."""
    task = {
        "task_id": "HARNESS-BOOTSTRAP-0001",
        "task_type": "standard",
        "evidence": {
            "tests": {"status": "passed", "skip_reason": None},
            "code_review": {
                "status": "skipped",
                "skip_reason": "Authorized by bootstrap-exception.yaml",
            },
            "security_review": {
                "status": "skipped",
                "skip_reason": "Authorized by bootstrap-exception.yaml",
            },
        },
    }
    result = validate(task, bootstrap_policy=_BOOTSTRAP_POLICY)
    assert result.valid, f"Errors: {result.errors}"


def test_bootstrap_task_without_gate_authorization_fails() -> None:
    """HARNESS-BOOTSTRAP-0001 but policy does NOT authorize code_review → FAIL."""
    task = {
        "task_id": "HARNESS-BOOTSTRAP-0001",
        "task_type": "standard",
        "evidence": {
            "tests": {"status": "passed", "skip_reason": None},
            "code_review": {
                "status": "skipped",
                "skip_reason": "I want to skip anyway",
            },
            "security_review": {
                "status": "skipped",
                "skip_reason": "Authorized by bootstrap-exception.yaml",
            },
        },
    }
    result = validate(task, bootstrap_policy=_BOOTSTRAP_POLICY_NO_CODE_REVIEW)
    assert not result.valid
    assert any("code_review" in e and "cannot be skipped" in e for e in result.errors)


def test_other_task_cannot_use_bootstrap_exception() -> None:
    """Another task_id trying to use the bootstrap policy → FAIL."""
    task = {
        "task_id": "TASK-0002",
        "task_type": "standard",
        "evidence": {
            "tests": {"status": "passed", "skip_reason": None},
            "code_review": {
                "status": "skipped",
                "skip_reason": "Trying to use bootstrap exception",
            },
            "security_review": {"status": "passed", "skip_reason": None},
        },
    }
    result = validate(task, bootstrap_policy=_BOOTSTRAP_POLICY)
    assert not result.valid
    assert any("cannot be skipped" in e for e in result.errors)


def test_bootstrap_with_empty_skip_reason_fails() -> None:
    """Bootstrap task with authorized skip but EMPTY skip_reason → FAIL."""
    task = {
        "task_id": "HARNESS-BOOTSTRAP-0001",
        "task_type": "standard",
        "evidence": {
            "tests": {"status": "passed", "skip_reason": None},
            "code_review": {"status": "skipped", "skip_reason": ""},
            "security_review": {
                "status": "skipped",
                "skip_reason": "Authorized by bootstrap-exception.yaml",
            },
        },
    }
    result = validate(task, bootstrap_policy=_BOOTSTRAP_POLICY)
    assert not result.valid
    assert any("skip_reason" in e for e in result.errors)


def test_bootstrap_tests_skipped_fails() -> None:
    """Bootstrap task cannot skip tests — only code_review and security_review are authorized."""
    task = {
        "task_id": "HARNESS-BOOTSTRAP-0001",
        "task_type": "standard",
        "evidence": {
            "tests": {"status": "skipped", "skip_reason": "Trying to skip tests"},
            "code_review": {
                "status": "skipped",
                "skip_reason": "Authorized by bootstrap-exception.yaml",
            },
            "security_review": {
                "status": "skipped",
                "skip_reason": "Authorized by bootstrap-exception.yaml",
            },
        },
    }
    result = validate(task, bootstrap_policy=_BOOTSTRAP_POLICY)
    assert not result.valid
    assert any("tests" in e and "cannot be skipped" in e for e in result.errors)
