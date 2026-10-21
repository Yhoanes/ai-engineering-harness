from dataclasses import dataclass


@dataclass
class DistributionManifest:
    include: list[str]
    exclude_defensive: list[str]
    generated: list[str]
