import re
import shutil
import tempfile
from pathlib import Path

from engine.context.loader import resolve_project_root
from engine.projects.models import ProjectDefinition, ProjectInitializationResult, ProjectState


def _read_marker(path: Path) -> str:
    """Reads a canonical STATUS marker from a file."""
    if not path.exists():
        return "NOT_FOUND"
    try:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("STATUS:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "UNKNOWN"


def _derive_lifecycle_and_workflow(
    req_status: str, arch_status: str, src_status: str
) -> tuple[str, str | None]:
    """Derives project lifecycle and next recommended workflow based on markers."""
    if (
        req_status == "NOT_DEFINED"
        and arch_status == "NOT_DEFINED"
        and src_status == "NOT_INITIALIZED"
    ):
        return "initialized", "analyze-requirement"
    elif req_status == "DEFINED" and arch_status != "APPROVED" and src_status == "NOT_INITIALIZED":
        return "requirements_defined", "design-solution"
    elif req_status == "DEFINED" and arch_status == "APPROVED" and src_status == "NOT_INITIALIZED":
        return "architecture_defined", "plan-task"
    elif src_status == "INITIALIZED":
        return "implementation_started", None
    else:
        return "inconsistent_markers", None


def inspect_project_state(repo_root: Path, project_key: str) -> ProjectState:
    warnings = []
    try:
        project_root = resolve_project_root(repo_root, project_key)
    except ValueError as e:
        warnings.append(str(e))
        return ProjectState(project_key, "invalid_project_key", "UNKNOWN", False, None, warnings)

    if not project_root.exists():
        warnings.append("Project does not exist.")
        return ProjectState(project_key, "not_found", "UNKNOWN", False, None, warnings)

    req_status = _read_marker(project_root / "requirements" / "README.md")
    arch_status = _read_marker(project_root / "architecture" / "README.md")
    src_status = _read_marker(project_root / "source" / "README.md")

    lifecycle, recommended_wf = _derive_lifecycle_and_workflow(req_status, arch_status, src_status)
    if lifecycle == "inconsistent_markers":
        warnings.append(
            f"Inconsistent markers found: req={req_status}, arch={arch_status}, src={src_status}"
        )

    current_phase = "UNKNOWN"
    try:
        curr_state = (project_root / "memory" / "current-state.md").read_text(encoding="utf-8")
        for line in curr_state.splitlines():
            if line.startswith("Current Phase:"):
                current_phase = line.split(":", 1)[1].strip()
    except Exception:
        pass

    return ProjectState(
        project_key=project_key,
        lifecycle=lifecycle,
        current_phase=current_phase,
        implementation_initialized=(src_status == "INITIALIZED"),
        recommended_next_workflow=recommended_wf,
        warnings=warnings,
    )


def initialize_project(
    repo_root: Path, definition: ProjectDefinition
) -> ProjectInitializationResult:
    try:
        target_root = resolve_project_root(repo_root, definition.project_key)
    except ValueError as e:
        raise ValueError(f"Invalid project definition: {e}") from None

    if target_root.exists():
        raise FileExistsError(
            f"Project '{definition.project_key}' already exists. No overwrite allowed."
        )

    template_dir = repo_root / "templates" / "project"
    if not template_dir.exists():
        raise RuntimeError("Universal project template missing in repo root.")

    projects_dir = repo_root / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    staging_path_str = tempfile.mkdtemp(prefix="harness-staging-", dir=str(projects_dir))
    staging_dir = Path(staging_path_str)

    created_files = []

    try:

        def _process_dir(src: Path, dst: Path):
            dst.mkdir(parents=True, exist_ok=True)
            for item in src.iterdir():
                if item.name in [
                    "__pycache__",
                    ".pytest_cache",
                    ".ruff_cache",
                    "dist",
                    "build",
                    ".coverage",
                    "egg-info",
                ]:
                    continue
                if item.is_dir():
                    _process_dir(item, dst / item.name)
                elif item.is_file():
                    content = item.read_bytes()
                    if b"\x00" in content:
                        raise ValueError(f"Unexpected binary file in template: {item.name}")
                    text = content.decode("utf-8")

                    text = text.replace("{{PROJECT_KEY}}", definition.project_key)
                    text = text.replace("{{PROJECT_NAME}}", definition.display_name)
                    text = text.replace("{{INITIAL_DESCRIPTION}}", definition.initial_description)
                    text = text.replace("{{CONFIRMED_FACTS}}", definition.confirmed_facts or "NONE")
                    text = text.replace(
                        "{{PRELIMINARY_DECISIONS}}",
                        definition.preliminary_technical_decisions or "NONE",
                    )

                    # Verify no unresolved placeholders
                    if "{{" in text and "}}" in text:
                        unresolved = set(re.findall(r"\{\{([A-Z_]+)\}\}", text))
                        if unresolved:
                            raise ValueError(f"Unresolved placeholders in template: {unresolved}")

                    out_path = dst / item.name
                    out_path.write_text(text, encoding="utf-8")
                    created_files.append(str(out_path.relative_to(staging_dir).as_posix()))

        _process_dir(template_dir, staging_dir)

        # Atomic rename. If target_root was created concurrently, Path.rename raises
        # FileExistsError (Windows/POSIX) or OSError (POSIX sometimes).
        if target_root.exists():
            raise FileExistsError(f"Target '{target_root.name}' was created concurrently.")

        staging_dir.rename(target_root)

    except Exception as e:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise e

    st = inspect_project_state(repo_root, definition.project_key)

    return ProjectInitializationResult(
        project_key=definition.project_key,
        project_root=str(target_root.relative_to(repo_root).as_posix()),
        created_files=created_files,
        lifecycle=st.lifecycle,
        recommended_next_workflow=st.recommended_next_workflow,
        warnings=st.warnings,
    )
