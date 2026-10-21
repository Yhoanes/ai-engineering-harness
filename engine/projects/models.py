from dataclasses import dataclass


@dataclass
class ProjectDefinition:
    project_key: str
    display_name: str
    initial_description: str
    confirmed_facts: str | None = None
    preliminary_technical_decisions: str | None = None


@dataclass
class ProjectState:
    project_key: str
    lifecycle: str
    current_phase: str
    implementation_initialized: bool
    recommended_next_workflow: str | None
    warnings: list[str]


@dataclass
class ProjectInitializationResult:
    project_key: str
    project_root: str
    created_files: list[str]
    lifecycle: str
    recommended_next_workflow: str | None
    warnings: list[str]
