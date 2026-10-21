import pytest

from engine.advisor.service import (
    discover_specialists,
    discover_workflows,
    get_general_guidance,
    get_guidance_for_request,
)
from engine.projects.manager import initialize_project
from engine.projects.models import ProjectDefinition


@pytest.fixture
def temp_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    # Mock specialists
    spec_dir = repo / "core" / "specialists" / "test-spec"
    spec_dir.mkdir(parents=True)
    (spec_dir / "specialist.yaml").write_text(
        "id: test-spec\npurpose: testing\ncapabilities: [a, b]", encoding="utf-8"
    )

    # Mock workflows
    wf_dir = repo / "core" / "workflows" / "test-wf"
    wf_dir.mkdir(parents=True)
    (wf_dir / "workflow.yaml").write_text(
        "id: test-wf\ndescription: testing wf\nallowed_specialists: [test-spec]", encoding="utf-8"
    )

    # Mock project template for initialize_project
    tpl = repo / "templates" / "project"
    tpl.mkdir(parents=True)
    (tpl / "README.md").write_text("Hi", encoding="utf-8")
    (tpl / "requirements").mkdir()
    (tpl / "requirements" / "README.md").write_text("STATUS: NOT_DEFINED", encoding="utf-8")
    (tpl / "architecture").mkdir()
    (tpl / "architecture" / "README.md").write_text("STATUS: NOT_DEFINED", encoding="utf-8")
    (tpl / "source").mkdir()
    (tpl / "source" / "README.md").write_text("STATUS: NOT_INITIALIZED", encoding="utf-8")
    (tpl / "memory").mkdir()
    (tpl / "memory" / "current-state.md").write_text("Current Phase: x", encoding="utf-8")

    return repo


def test_discover_specialists(temp_repo):
    specs = discover_specialists(temp_repo)
    assert len(specs) == 1
    assert specs[0]["id"] == "test-spec"
    assert specs[0]["capabilities"] == ["a", "b"]
    assert specs[0]["limitations"] == []  # Defaults to [] if missing


def test_discover_workflows(temp_repo):
    wfs = discover_workflows(temp_repo)
    assert len(wfs) == 1
    assert wfs[0]["id"] == "test-wf"
    assert wfs[0]["description"] == "testing wf"
    assert wfs[0]["allowed_specialists"] == ["test-spec"]


def test_no_project_guidance(temp_repo):
    g = get_general_guidance(temp_repo, None)
    assert "no project is selected" in g.message
    assert "no project yet" in g.blockers
    assert not g.requires_task_contract
    assert g.next_user_action == "Define project intent"


def test_project_not_found(temp_repo):
    g = get_general_guidance(temp_repo, "ghost")
    assert "not physically initialized yet" in g.message
    assert "Project does not exist physically." in g.blockers
    assert g.requires_task_contract


def test_project_initialized(temp_repo):
    pdef = ProjectDefinition("t1", "T1", "Desc")
    initialize_project(temp_repo, pdef)

    g = get_general_guidance(temp_repo, "t1")
    assert "next step is analyze-requirement" in g.message
    assert g.lifecycle_state == "initialized"
    assert g.recommended_workflow == "analyze-requirement"
    assert g.requires_task_contract


def test_project_requirements_defined(temp_repo):
    pdef = ProjectDefinition("t1", "T1", "Desc")
    initialize_project(temp_repo, pdef)
    (temp_repo / "projects" / "t1" / "requirements" / "README.md").write_text(
        "STATUS: DEFINED", encoding="utf-8"
    )

    g = get_general_guidance(temp_repo, "t1")
    assert "next step is design-solution" in g.message
    assert g.lifecycle_state == "requirements_defined"
    assert g.recommended_workflow == "design-solution"


def test_inconsistent_markers(temp_repo):
    pdef = ProjectDefinition("t1", "T1", "Desc")
    initialize_project(temp_repo, pdef)
    (temp_repo / "projects" / "t1" / "architecture" / "README.md").write_text(
        "STATUS: APPROVED", encoding="utf-8"
    )

    g = get_general_guidance(temp_repo, "t1")
    assert "inconsistent" in g.message
    assert "Inconsistent project markers" in g.blockers[0]


def test_intent_evolution_harness_itself(temp_repo):
    # Missing evolution advisor in temp_repo
    g = get_guidance_for_request(temp_repo, "I want to improve the AI Engineering Harness itself.")
    assert "EVOLUTION_ADVISOR_NOT_INSTALLED" in g.blockers

    # Mock the evolution advisor
    (temp_repo / "core" / "specialists" / "harness-evolution-advisor").mkdir()
    (
        temp_repo / "core" / "specialists" / "harness-evolution-advisor" / "specialist.yaml"
    ).write_text("id: harness-evolution-advisor", encoding="utf-8")

    g2 = get_guidance_for_request(temp_repo, "I want to improve the AI Engineering Harness itself.")
    assert "harness-evolution-advisor" in g2.recommended_specialists
    assert g2.recommended_workflow == "discuss"
    assert g2.requires_human_approval is True


def test_intent_evolution_add_skill(temp_repo):
    (temp_repo / "core" / "specialists" / "harness-evolution-advisor").mkdir(exist_ok=True)
    (
        temp_repo / "core" / "specialists" / "harness-evolution-advisor" / "specialist.yaml"
    ).write_text("id: harness-evolution-advisor", encoding="utf-8")

    g = get_guidance_for_request(temp_repo, "I want to add a reusable Skill to the Harness.")
    assert "harness-evolution-advisor" in g.recommended_specialists


def test_intent_evolution_add_host(temp_repo):
    (temp_repo / "core" / "specialists" / "harness-evolution-advisor").mkdir(exist_ok=True)
    (
        temp_repo / "core" / "specialists" / "harness-evolution-advisor" / "specialist.yaml"
    ).write_text("id: harness-evolution-advisor", encoding="utf-8")

    g = get_guidance_for_request(
        temp_repo, "I want to add support for a new host environment to the harness."
    )
    assert "harness-evolution-advisor" in g.recommended_specialists


def test_intent_evolution_add_local_model(temp_repo):
    (temp_repo / "core" / "specialists" / "harness-evolution-advisor").mkdir(exist_ok=True)
    (
        temp_repo / "core" / "specialists" / "harness-evolution-advisor" / "specialist.yaml"
    ).write_text("id: harness-evolution-advisor", encoding="utf-8")

    g = get_guidance_for_request(
        temp_repo, "I want to support a local model runtime in the Harness."
    )
    assert "harness-evolution-advisor" in g.recommended_specialists


def test_intent_evolution_add_specialist(temp_repo):
    (temp_repo / "core" / "specialists" / "harness-evolution-advisor").mkdir(exist_ok=True)
    (
        temp_repo / "core" / "specialists" / "harness-evolution-advisor" / "specialist.yaml"
    ).write_text("id: harness-evolution-advisor", encoding="utf-8")

    g = get_guidance_for_request(temp_repo, "I want to add a new specialist to the Harness.")
    assert "harness-evolution-advisor" in g.recommended_specialists


def test_intent_project_false_positive_auth(temp_repo):
    g = get_guidance_for_request(temp_repo, "I want to add authentication to my application.")
    assert "harness-evolution-advisor" not in g.recommended_specialists
    # Falls back to general guidance
    assert "general-advisor" in g.recommended_specialists


def test_intent_project_false_positive_db(temp_repo):
    g = get_guidance_for_request(temp_repo, "I want to design my project's database.")
    assert "harness-evolution-advisor" not in g.recommended_specialists
