import pytest

from engine.projects.manager import initialize_project, inspect_project_state
from engine.projects.models import ProjectDefinition


@pytest.fixture
def temp_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    # Create the template directory
    template_dir = repo / "templates" / "project"
    template_dir.mkdir(parents=True)

    (template_dir / "README.md").write_text("Hello {{PROJECT_NAME}}", encoding="utf-8")

    req_dir = template_dir / "requirements"
    req_dir.mkdir()
    (req_dir / "README.md").write_text("STATUS: NOT_DEFINED\n\nreqs", encoding="utf-8")

    arch_dir = template_dir / "architecture"
    arch_dir.mkdir()
    (arch_dir / "README.md").write_text("STATUS: NOT_DEFINED\n\narch", encoding="utf-8")

    src_dir = template_dir / "source"
    src_dir.mkdir()
    (src_dir / "README.md").write_text("STATUS: NOT_INITIALIZED\n\nsrc", encoding="utf-8")

    mem_dir = template_dir / "memory"
    mem_dir.mkdir()
    (mem_dir / "current-state.md").write_text("Current Phase: initial\n", encoding="utf-8")

    return repo


def test_initialization_complete(temp_repo):
    pdef = ProjectDefinition(
        project_key="test_proj",
        display_name="Test Project",
        initial_description="Desc",
        confirmed_facts="Fact 1",
        preliminary_technical_decisions="Dec 1",
    )
    result = initialize_project(temp_repo, pdef)
    assert result.project_key == "test_proj"
    assert result.lifecycle == "initialized"
    assert result.recommended_next_workflow == "analyze-requirement"

    # Check creation
    proj_dir = temp_repo / "projects" / "test_proj"
    assert proj_dir.exists()
    assert (proj_dir / "README.md").read_text(encoding="utf-8") == "Hello Test Project"


def test_no_overwrite(temp_repo):
    pdef = ProjectDefinition("test_proj", "Test Project", "Desc")
    initialize_project(temp_repo, pdef)

    with pytest.raises(FileExistsError):
        initialize_project(temp_repo, pdef)


def test_invalid_keys(temp_repo):
    invalid_keys = ["../escape", "a/b", "c\\d", " ", ""]
    for key in invalid_keys:
        pdef = ProjectDefinition(key, "Test", "Desc")
        with pytest.raises(ValueError, match="Invalid project|escapes"):
            initialize_project(temp_repo, pdef)


def test_inspect_states(temp_repo):
    pdef = ProjectDefinition("st_proj", "St Project", "Desc")
    initialize_project(temp_repo, pdef)

    proj_dir = temp_repo / "projects" / "st_proj"

    # Initial state
    st = inspect_project_state(temp_repo, "st_proj")
    assert st.lifecycle == "initialized"
    assert st.recommended_next_workflow == "analyze-requirement"

    # Change requirements
    (proj_dir / "requirements" / "README.md").write_text("STATUS: DEFINED", encoding="utf-8")
    st = inspect_project_state(temp_repo, "st_proj")
    assert st.lifecycle == "requirements_defined"
    assert st.recommended_next_workflow == "design-solution"

    # Change architecture
    (proj_dir / "architecture" / "README.md").write_text("STATUS: APPROVED", encoding="utf-8")
    st = inspect_project_state(temp_repo, "st_proj")
    assert st.lifecycle == "architecture_defined"
    assert st.recommended_next_workflow == "plan-task"

    # Initialize source
    (proj_dir / "source" / "README.md").write_text("STATUS: INITIALIZED", encoding="utf-8")
    st = inspect_project_state(temp_repo, "st_proj")
    assert st.lifecycle == "implementation_started"
    assert st.recommended_next_workflow is None


def test_inconsistent_markers(temp_repo):
    pdef = ProjectDefinition("st_proj", "St Project", "Desc")
    initialize_project(temp_repo, pdef)

    proj_dir = temp_repo / "projects" / "st_proj"
    # Arch approved but req NOT_DEFINED
    (proj_dir / "architecture" / "README.md").write_text("STATUS: APPROVED", encoding="utf-8")
    st = inspect_project_state(temp_repo, "st_proj")
    assert st.lifecycle == "inconsistent_markers"
    assert "Inconsistent markers found" in st.warnings[0]


def test_unresolved_placeholder(temp_repo):
    # Add a mandatory placeholder that we don't resolve
    (temp_repo / "templates" / "project" / "README.md").write_text(
        "Hello {{UNEXPECTED}}", encoding="utf-8"
    )
    pdef = ProjectDefinition("test_proj", "Test", "Desc")
    with pytest.raises(ValueError, match="Unresolved placeholders"):
        initialize_project(temp_repo, pdef)
    # Ensure staging was cleaned up
    projects_dir = temp_repo / "projects"
    # Should only have no staging dirs
    for item in projects_dir.iterdir():
        assert "harness-staging" not in item.name
    # Destination should not exist
    assert not (projects_dir / "test_proj").exists()


def test_inspect_not_found(temp_repo):
    st = inspect_project_state(temp_repo, "non_existent")
    assert st.lifecycle == "not_found"
    assert st.current_phase == "UNKNOWN"
