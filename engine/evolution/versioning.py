from engine.evolution.models import ExtensionProposal, ExtensionType


def recommend_version_change(proposal: ExtensionProposal) -> str:
    """Recommend Semantic Versioning bump based on extension impact."""
    if proposal.governance_changes_required or proposal.migration_required:
        return "MAJOR"

    if proposal.extension_type in (
        ExtensionType.SPECIALIST,
        ExtensionType.SKILL,
        ExtensionType.ADAPTER,
        ExtensionType.PROVIDER,
        ExtensionType.WORKFLOW,
    ):
        return "MINOR"

    return "PATCH"
