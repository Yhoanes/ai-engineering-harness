from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextBundle:
    project: str
    requested_level: int
    loaded_level: int
    sources: dict[str, str] = field(default_factory=dict)
    missing_sources: list[str] = field(default_factory=list)
    content_sections: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
