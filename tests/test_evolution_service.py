from engine.evolution.models import ExtensionRequest, ExtensionType
from engine.evolution.service import EvolutionService


def test_evolution_service_classification():
    service = EvolutionService()

    cases = [
        ("Add a new specialist for testing", "test automation", ExtensionType.SPECIALIST),
        ("Create a reusable Django bootstrap capability", "django init", ExtensionType.SKILL),
        ("Support OpenCode as a host", "opencode integration", ExtensionType.ADAPTER),
        ("Use a local model runtime", "run models locally", ExtensionType.PROVIDER),
        ("Enforce repository cleanup rules", "cleanup rule", ExtensionType.POLICY),
        ("Change reusable project starter files", "update starter", ExtensionType.TEMPLATE),
        ("Add a deterministic governance gate", "security gate", ExtensionType.VALIDATOR),
        ("Add a governed implementation process", "new process", ExtensionType.WORKFLOW),
    ]

    for desc, cap, expected in cases:
        req = ExtensionRequest(description=desc, requested_capability=cap)
        assert service.classify_extension_request(req) == expected


def test_evolution_service_proposal_self_mod():
    service = EvolutionService()
    req = ExtensionRequest(
        description="Improve the Evolution Advisor", requested_capability="Add feature"
    )
    proposal = service.build_extension_proposal("harness-evolution-advisor", req)

    assert proposal.governance_changes_required is True
    assert proposal.extension_type == ExtensionType.SPECIALIST
    assert proposal.suggested_version_bump in ("MINOR", "MAJOR")


def test_evolution_service_provider_detection():
    service = EvolutionService()
    req = ExtensionRequest(
        description="Work offline with local models", requested_capability="offline runtime"
    )
    proposal = service.build_extension_proposal("local-llm", req)

    assert proposal.extension_type == ExtensionType.PROVIDER
    assert proposal.provider_requirement is not None
    assert proposal.provider_requirement.external_runtime_required is True
    assert "optional_runtime" in proposal.installer_impact
