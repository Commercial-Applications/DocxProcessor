from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml


@dataclass
class RegexTransform:
    """Single regex transformation rule."""

    from_pattern: str
    to_pattern: str


@dataclass
class TransformConfig:
    """Configuration for document transformations."""

    url_transforms: List[RegexTransform]
    text_transforms: List[RegexTransform]
    style_transforms: List[RegexTransform]
    drop_matches: List[str]

    @classmethod
    def from_yaml(cls, config_path: Path) -> "TransformConfig":
        """Load transformation configuration from YAML file."""
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
        return cls(
            url_transforms=[RegexTransform(t["from"], t["to"]) for t in config_data.get("url_transforms", [])],
            text_transforms=[RegexTransform(t["from"], t["to"]) for t in config_data.get("text_transforms", [])],
            style_transforms=[RegexTransform(t["from"], t["to"]) for t in config_data.get("style_transforms", [])],
            drop_matches=config_data.get("drop_matches", []),
        )


@dataclass
class RuntimeConfig:
    """Configuration from CLI arguments."""

    source_dir: Path
    destination_dir: Path
    log_file: Path
    log_level: str
    workers: int
    sync_mode: bool
    find_only: bool
    verbose: int


@dataclass
class AppConfig:
    """Combined application configuration."""

    transform: TransformConfig
    runtime: RuntimeConfig
