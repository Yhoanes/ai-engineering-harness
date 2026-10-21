from engine.evolution.models import (
    ExtensionProposal,
    ExtensionRequest,
    ExtensionType,
    ProviderRequirement,
)
from engine.evolution.versioning import recommend_version_change


class EvolutionService:
    """Read-only service for classifying and proposing extensions."""

    def classify_extension_request(self, request: ExtensionRequest) -> ExtensionType:
        """Deterministically classify an extension request."""
        desc = request.description.lower() + " " + request.requested_capability.lower()

        if "specialist" in desc or "advisor" in desc:
            return ExtensionType.SPECIALIST
        if "workflow" in desc or "process" in desc:
            return ExtensionType.WORKFLOW
        if "adapter" in desc or "host integration" in desc or "opencode" in desc or "codex" in desc:
            return ExtensionType.ADAPTER
        if (
            "provider" in desc
            or "model runtime" in desc
            or "local model" in desc
            or "ollama" in desc
        ):
            return ExtensionType.PROVIDER
        if "reusable" in desc and "capability" in desc or "skill" in desc:
            return ExtensionType.SKILL
        if "policy" in desc or "rule" in desc or "enforce" in desc:
            return ExtensionType.POLICY
        if "template" in desc or "starter file" in desc or "scaffold" in desc:
            return ExtensionType.TEMPLATE
        if "validator" in desc or "gate" in desc:
            return ExtensionType.VALIDATOR

        return ExtensionType.SKILL  # Default to SKILL if ambiguous

    def build_extension_proposal(
        self, proposed_id: str, request: ExtensionRequest
    ) -> ExtensionProposal:
        ext_type = self.classify_extension_request(request)

        # Check self-modification and authority
        is_self_mod = (
            proposed_id == "harness-evolution-advisor"
            or "evolution advisor" in request.description.lower()
        )
        governance_required = is_self_mod

        provider_req = None
        if ext_type == ExtensionType.PROVIDER or "local model" in request.description.lower():
            provider_req = ProviderRequirement(
                provider_kind="local_model_runtime"
                if "local" in request.description.lower()
                else "cloud_model_runtime",
                external_runtime_required="local" in request.description.lower(),
            )

        affected = []
        if ext_type == ExtensionType.SPECIALIST:
            affected.append(f"core/specialists/{proposed_id}/**")
        elif ext_type == ExtensionType.SKILL:
            affected.append(f"skills/{proposed_id}/**")

        proposal = ExtensionProposal(
            extension_type=ext_type,
            proposed_id=proposed_id,
            rationale=f"Proposed {ext_type.value} for {request.requested_capability}",
            affected_components=affected,
            required_specialists=["harness-maintainer"],
            recommended_workflow="implement-task",
            required_tests=[f"tests/test_{proposed_id.replace('-', '_')}.py"],
            security_review_required=True,
            governance_changes_required=governance_required,
            authority_gaps=[],
            migration_required=False,
            installer_impact=["optional_runtime"] if provider_req else [],
            distribution_impact=["skills/**"] if ext_type == ExtensionType.SKILL else [],
            suggested_version_bump="",  # filled below
            blockers=[],
            next_action="Create Task Contract",
            provider_requirement=provider_req,
        )

        # Bypass frozen constraints to set the derived semantic version bump
        object.__setattr__(proposal, "suggested_version_bump", recommend_version_change(proposal))
        return proposal
