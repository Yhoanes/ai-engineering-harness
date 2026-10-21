from __future__ import annotations

import json
from pathlib import Path

from engine.orchestrator.models import OrchestratorHandoff


def _load_safe(repo_root: Path, rel_path: str) -> str:
    resolved_root = repo_root.resolve()
    resolved_candidate = (repo_root / rel_path).resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        raise ValueError(f"Path traversal detected: {rel_path}") from None
    if not resolved_candidate.is_file():
        raise FileNotFoundError(f"Required prompt file missing: {rel_path}")
    return resolved_candidate.read_text(encoding="utf-8")


def build_prompt(
    repo_root: Path,
    handoff: OrchestratorHandoff,
    user_input: str,
    conversation_context: str | None = None,
) -> dict[str, str | list[str]]:
    """
    Builds the deterministic execution prompt pieces and the final assembled string.
    Returns a dict with pieces and 'final_prompt'.
    """
    # 1. SYSTEM / GOVERNANCE (shared rules)
    governance_parts = []
    gov_files = [
        "core/specialists/_shared/preamble.md",
        "core/specialists/_shared/human-gate-rules.md",
        "core/specialists/_shared/source-of-truth-rules.md",
        "core/specialists/_shared/task-contract-rules.md",
    ]
    import contextlib

    for gf in gov_files:
        with contextlib.suppress(FileNotFoundError):
            governance_parts.append(_load_safe(repo_root, gf))

    if not governance_parts:
        governance_parts.append("STRICT GOVERNANCE ENFORCED.")

    system_governance = "\n\n".join(governance_parts)

    # 2. SOURCE OF TRUTH (Implicit in rules)
    # 3. SHARED SPECIALIST RULES & 4. SPECIALIST PROMPT
    specialist_prompt = _load_safe(
        repo_root, f"core/specialists/{handoff.primary_specialist}/prompt.md"
    )

    # 5. SHARED WORKFLOW RULES & 6. WORKFLOW PROMPT
    workflow_prompt = _load_safe(repo_root, f"core/workflows/{handoff.workflow}/prompt.md")

    # 7. CONTEXT
    context_payload = ""
    if handoff.context_bundle:
        context_payload += "--- CONTEXT BUNDLE ---\n"
        for title, content in handoff.context_bundle.content_sections.items():
            context_payload += f"[{title}]\n{content}\n\n"

    # 8. TASK CONTRACT / RESTRICTIONS
    contract_str = ""
    if handoff.task_contract:
        contract_str += "--- TASK CONTRACT ---\n"
        contract_str += json.dumps(handoff.task_contract, indent=2) + "\n"

    rest_str = ""
    if handoff.restrictions:
        rest_str += "--- RESTRICTIONS ---\n"
        for r in handoff.restrictions:
            rest_str += f"- {r}\n"

    # 9. USER REQUEST
    user_str = "--- UNTRUSTED USER INPUT ---\n"
    if conversation_context:
        user_str += "--- UNTRUSTED / INFORMATIONAL ONLY CONVERSATION CONTEXT ---\n"
        user_str += conversation_context + "\n"
    user_str += "USER REQUEST:\n" + user_input + "\n"

    # 10. OUTPUT CONTRACT
    expected_output_contract = [
        "summary",
        "findings",
        "actions_performed",
        "files_changed",
        "validations",
        "blockers",
        "warnings",
        "next_action",
    ]
    output_str = "--- OUTPUT CONTRACT ---\nExpected JSON keys in structured output:\n"
    for k in expected_output_contract:
        output_str += f"- {k}\n"

    final_prompt = (
        f"{system_governance}\n\n"
        f"--- SPECIALIST ---\n{specialist_prompt}\n\n"
        f"--- WORKFLOW ---\n{workflow_prompt}\n\n"
        f"{context_payload}\n"
        f"{contract_str}\n"
        f"{rest_str}\n"
        f"{user_str}\n"
        f"{output_str}"
    )

    return {
        "specialist_prompt": specialist_prompt,
        "workflow_prompt": workflow_prompt,
        "context_payload": context_payload,
        "expected_output_contract": expected_output_contract,
        "final_prompt": final_prompt,
    }
