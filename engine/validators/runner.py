from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.validators import ValidationResult
from engine.validators.validate_acceptance_gate import validate as validate_acceptance_gate
from engine.validators.validate_allowed_paths_post import validate as validate_allowed_paths_post
from engine.validators.validate_allowed_paths_pre import validate as validate_allowed_paths_pre
from engine.validators.validate_approval_gate import validate as validate_approval_gate
from engine.validators.validate_authority import validate as validate_authority
from engine.validators.validate_deviation import validate as validate_deviation
from engine.validators.validate_evidence import validate as validate_evidence
from engine.validators.validate_preconditions import validate as validate_preconditions
from engine.validators.validate_task_contract import validate as validate_task_contract
from engine.validators.validate_transition import validate as validate_transition


@dataclass
class RunnerResult:
    """Aggregated result from running a validation chain."""

    all_passed: bool
    results: list[ValidationResult] = field(default_factory=list)
    not_applicable: list[dict[str, str]] = field(default_factory=list)


# Validator chain definitions per transition
TRANSITION_CHAINS: dict[str, list[str]] = {
    "draft -> awaiting_approval": ["validate_task_contract", "validate_preconditions"],
    "awaiting_approval -> approved": ["validate_transition", "validate_approval_gate"],
    "awaiting_approval -> rejected": ["validate_transition"],
    "approved -> in_progress": [
        "validate_transition",
        "validate_allowed_paths_pre",
        "validate_authority",
        "validate_preconditions",
    ],
    "in_progress -> blocked": ["validate_transition"],
    "blocked -> in_progress": ["validate_transition"],
    "in_progress -> completed": [
        "validate_transition",
        "validate_allowed_paths_post",
        "validate_evidence",
        "validate_acceptance_gate",
    ],
    "in_progress -> completed_with_deviation": [
        "validate_transition",
        "validate_allowed_paths_post",
        "validate_evidence",
        "validate_acceptance_gate",
        "validate_deviation",
    ],
    "in_progress -> rejected": ["validate_transition"],
}

ACTION_CHAINS: dict[str, list[str]] = {
    "modify_file": ["validate_authority", "validate_allowed_paths_pre"],
    "invoke_specialist": ["validate_authority", "validate_preconditions"],
    "create_task": ["validate_task_contract", "validate_authority"],
}

VALIDATOR_MAP: dict[str, Any] = {
    "validate_task_contract": validate_task_contract,
    "validate_transition": validate_transition,
    "validate_approval_gate": validate_approval_gate,
    "validate_acceptance_gate": validate_acceptance_gate,
    "validate_allowed_paths_pre": validate_allowed_paths_pre,
    "validate_allowed_paths_post": validate_allowed_paths_post,
    "validate_authority": validate_authority,
    "validate_preconditions": validate_preconditions,
    "validate_evidence": validate_evidence,
    "validate_deviation": validate_deviation,
}


def run_transition_chain(
    from_status: str,
    to_status: str,
    task: dict,
    *,
    authority_matrix: dict | None = None,
    actual_paths: list[str] | None = None,
    workflows: dict | None = None,
) -> RunnerResult:
    """Run the validation chain for a state transition."""
    key = f"{from_status} -> {to_status}"
    chain = TRANSITION_CHAINS.get(key)
    if chain is None:
        return RunnerResult(
            all_passed=False,
            results=[
                ValidationResult(
                    valid=False,
                    validator_id="runner",
                    errors=[f"No validation chain defined for transition: {key}"],
                )
            ],
        )

    return _run_chain(
        chain,
        task=task,
        from_status=from_status,
        to_status=to_status,
        authority_matrix=authority_matrix,
        actual_paths=actual_paths,
        workflows=workflows,
    )


def run_action_chain(
    action: str,
    task: dict,
    *,
    specialist_id: str | None = None,
    authority_matrix: dict | None = None,
    target_paths: list[str] | None = None,
    workflows: dict | None = None,
) -> RunnerResult:
    """Run the validation chain for an action."""
    chain = ACTION_CHAINS.get(action)
    if chain is None:
        return RunnerResult(
            all_passed=False,
            results=[
                ValidationResult(
                    valid=False,
                    validator_id="runner",
                    errors=[f"No validation chain defined for action: {action}"],
                )
            ],
        )

    return _run_chain(
        chain,
        task=task,
        specialist_id=specialist_id,
        authority_matrix=authority_matrix,
        target_paths=target_paths,
        workflows=workflows,
    )


def _run_chain(
    chain: list[str],
    *,
    task: dict,
    from_status: str | None = None,
    to_status: str | None = None,
    specialist_id: str | None = None,
    authority_matrix: dict | None = None,
    actual_paths: list[str] | None = None,
    target_paths: list[str] | None = None,
    workflows: dict | None = None,
) -> RunnerResult:
    """Execute a list of validators, stopping on first failure."""
    results: list[ValidationResult] = []
    not_applicable: list[dict[str, str]] = []

    for validator_name in chain:
        validator_fn = VALIDATOR_MAP.get(validator_name)
        if validator_fn is None:
            not_applicable.append({"validator": validator_name, "reason": "Validator not found"})
            continue

        try:
            result = _call_validator(
                validator_name,
                validator_fn,
                task=task,
                from_status=from_status,
                to_status=to_status,
                specialist_id=specialist_id,
                authority_matrix=authority_matrix,
                actual_paths=actual_paths,
                target_paths=target_paths,
                workflows=workflows,
            )
            results.append(result)
            if not result.valid:
                return RunnerResult(
                    all_passed=False,
                    results=results,
                    not_applicable=not_applicable,
                )
        except TypeError:
            not_applicable.append(
                {"validator": validator_name, "reason": "Missing required parameters"}
            )

    all_passed = all(r.valid for r in results)
    return RunnerResult(all_passed=all_passed, results=results, not_applicable=not_applicable)


def _call_validator(
    name: str,
    fn: Any,
    *,
    task: dict,
    from_status: str | None = None,
    to_status: str | None = None,
    specialist_id: str | None = None,
    authority_matrix: dict | None = None,
    actual_paths: list[str] | None = None,
    target_paths: list[str] | None = None,
    workflows: dict | None = None,
) -> ValidationResult:
    """Call a validator with the appropriate arguments."""
    if name == "validate_task_contract":
        return fn(task)
    if name == "validate_transition":
        return fn(from_status or task.get("status", ""), to_status or "")
    if name == "validate_approval_gate":
        return fn(task)
    if name == "validate_acceptance_gate":
        return fn(task)
    if name == "validate_allowed_paths_pre":
        return fn(task, authority_matrix=authority_matrix)
    if name == "validate_allowed_paths_post":
        return fn(task, actual_paths=actual_paths or [])
    if name == "validate_authority":
        specialist = specialist_id or (
            task.get("assigned_specialists", [None])[0]
            if task.get("assigned_specialists")
            else None
        )
        return fn(specialist or "", task, authority_matrix=authority_matrix)
    if name == "validate_preconditions":
        return fn(task, workflows=workflows)
    if name == "validate_evidence":
        return fn(task)
    if name == "validate_deviation":
        return fn(task)
    return ValidationResult(valid=False, validator_id=name, errors=["Unknown validator"])
