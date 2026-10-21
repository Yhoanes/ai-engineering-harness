from dataclasses import dataclass, field
from enum import StrEnum


class ExtensionType(StrEnum):
    SPECIALIST = "SPECIALIST"
    WORKFLOW = "WORKFLOW"
    SKILL = "SKILL"
    ADAPTER = "ADAPTER"
    PROVIDER = "PROVIDER"
    POLICY = "POLICY"
    TEMPLATE = "TEMPLATE"
    VALIDATOR = "VALIDATOR"


@dataclass(frozen=True)
class ProviderRequirement:
    provider_kind: str
    external_runtime_required: bool


@dataclass(frozen=True)
class ExtensionRequest:
    description: str
    requested_capability: str
    target_host: str | None = None
    constraints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExtensionProposal:
    extension_type: ExtensionType
    proposed_id: str
    rationale: str
    affected_components: list[str]
    required_specialists: list[str]
    recommended_workflow: str
    required_tests: list[str]
    security_review_required: bool
    governance_changes_required: bool
    authority_gaps: list[str]
    migration_required: bool
    installer_impact: list[str]
    distribution_impact: list[str]
    suggested_version_bump: str
    blockers: list[str]
    next_action: str
    provider_requirement: ProviderRequirement | None = None
