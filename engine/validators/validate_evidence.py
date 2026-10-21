from __future__ import annotations

from pathlib import Path

import yaml

from engine.validators import ValidationResult

# Default path to bootstrap exception policy (relative to repo root)
_BOOTSTRAP_POLICY_REL = Path("core/policies/bootstrap-exception.yaml")


def _load_bootstrap_policy(repo_root: Path | None = None) -> dict | None:
    """Load the bootstrap exception policy from disk."""
    if repo_root is None:
        return None
    policy_path = repo_root / _BOOTSTRAP_POLICY_REL
    if not policy_path.exists():
        return None
    with policy_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _is_gate_authorized_by_bootstrap(
    task_id: str,
    gate_name: str,
    policy: dict | None,
) -> bool:
    """Check if a specific gate skip is authorized by the bootstrap exception policy.

    Authorization requires:
    1. The policy exists and contains an exception block.
    2. The exception.id matches the task_id exactly.
    3. The gate_name is listed in exception.authorized_skips.
    4. The authorized skip has status == 'skipped'.
    """
    if policy is None:
        return False
    exception = policy.get("exception", {})
    if exception.get("id") != task_id:
        return False
    authorized_skips = exception.get("authorized_skips", {})
    gate_auth = authorized_skips.get(gate_name)
    if gate_auth is None:
        return False
    return gate_auth.get("status") == "skipped"


def validate(
    task: dict,
    *,
    repo_root: Path | None = None,
    bootstrap_policy: dict | None = None,
) -> ValidationResult:
    """Validate that required evidence is present and skip_reason is provided when skipped.

    For standard tasks, tests and code_review cannot be skipped UNLESS
    the bootstrap exception policy explicitly authorizes the skip for the
    exact task_id.
    """
    errors: list[str] = []
    warnings: list[str] = []

    evidence = task.get("evidence", {})
    task_type = task.get("task_type", "standard")
    task_id = task.get("task_id", "")

    # Load bootstrap policy if not provided
    policy = bootstrap_policy
    if policy is None and repo_root is not None:
        policy = _load_bootstrap_policy(repo_root)

    for gate_name in ["tests", "code_review", "security_review"]:
        gate = evidence.get(gate_name, {})
        status = gate.get("status")

        if status is None:
            # Evidence not yet recorded — might be OK depending on phase
            warnings.append(f"evidence.{gate_name}.status is null")
            continue

        if status == "skipped":
            skip_reason = gate.get("skip_reason")
            if not skip_reason or not isinstance(skip_reason, str) or not skip_reason.strip():
                errors.append(
                    f"evidence.{gate_name}.status is 'skipped' but skip_reason is missing or empty"
                )

            # For standard tasks, tests and code_review cannot be skipped
            # UNLESS authorized by the bootstrap exception policy
            if (
                task_type == "standard"
                and gate_name in ("tests", "code_review")
                and not _is_gate_authorized_by_bootstrap(task_id, gate_name, policy)
            ):
                errors.append(f"evidence.{gate_name} cannot be skipped for standard tasks")

        elif status in ("failed", "changes_requested", "flagged"):
            warnings.append(
                f"evidence.{gate_name}.status is '{status}' — "
                f"task should not proceed to acceptance without resolution"
            )

    return ValidationResult(
        valid=len(errors) == 0,
        validator_id="validate_evidence",
        errors=errors,
        warnings=warnings,
    )
