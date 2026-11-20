import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml

TRANSFORM_KEYS = ("url_transforms", "text_transforms", "style_transforms")
ALLOWED_KEYS = TRANSFORM_KEYS + ("drop_matches",)


class ConfigError(ValueError):
    """The transforms configuration file is invalid."""


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
        """Load and validate transformation configuration from a YAML file.

        Raises ConfigError with a message naming the problem (file, key and rule number), so a bad
        configuration is reported before any document is processed.
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"{config_path}: invalid YAML: {e}") from e

        config_data = config_data or {}  # an empty file is a valid (empty) configuration
        if not isinstance(config_data, dict):
            raise ConfigError(f"{config_path}: expected a mapping of {', '.join(ALLOWED_KEYS)} at the top level")
        unknown = sorted(set(config_data) - set(ALLOWED_KEYS))
        if unknown:
            raise ConfigError(
                f"{config_path}: unknown key(s) {', '.join(unknown)}; expected any of {', '.join(ALLOWED_KEYS)}"
            )

        transforms = {key: cls._load_rules(config_path, key, config_data.get(key)) for key in TRANSFORM_KEYS}
        drop_matches = config_data.get("drop_matches") or []
        if not isinstance(drop_matches, list) or not all(isinstance(d, str) for d in drop_matches):
            raise ConfigError(f"{config_path}: drop_matches must be a list of strings")

        config = cls(drop_matches=drop_matches, **transforms)
        config.validate_patterns(str(config_path))
        return config

    @staticmethod
    def _load_rules(config_path: Path, key: str, rules) -> List[RegexTransform]:
        if rules is None:
            return []
        if not isinstance(rules, list):
            raise ConfigError(f"{config_path}: {key} must be a list of {{from, to}} rules")
        loaded = []
        for i, rule in enumerate(rules, 1):
            if (
                not isinstance(rule, dict)
                or not isinstance(rule.get("from"), str)
                or not isinstance(rule.get("to"), str)
            ):
                raise ConfigError(f"{config_path}: {key} rule {i} must have string 'from' and 'to' values: {rule!r}")
            loaded.append(RegexTransform(rule["from"], rule["to"]))
        return loaded

    def validate_patterns(self, source: str = "configuration") -> None:
        """Compile every URL and text rule (pattern and replacement); raise ConfigError on the first bad one.

        Style rules are exact style names, not regular expressions, so they are not compiled.
        """
        for key, flags in (("url_transforms", re.IGNORECASE), ("text_transforms", 0)):
            for i, rule in enumerate(getattr(self, key), 1):
                try:
                    pattern = re.compile(rule.from_pattern, flags)
                    # Substituting into an empty string checks the replacement template (group references).
                    pattern.sub(rule.to_pattern, "")
                except (re.error, IndexError) as e:
                    raise ConfigError(
                        f"{source}: {key} rule {i} (from: {rule.from_pattern!r}, to: {rule.to_pattern!r}): {e}"
                    ) from e

    @property
    def is_empty(self) -> bool:
        return not (self.url_transforms or self.text_transforms or self.style_transforms)


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
