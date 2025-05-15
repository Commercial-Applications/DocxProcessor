from dataclasses import dataclass
from pathlib import Path
import configparser
from typing import Optional

@dataclass
class Config:
    source_dir: Path
    destination_dir: Path
    debug_level: str
    find_regex: str
    from_regex: str
    to_regex_replace: str
    style_mappings: dict[str, str]
    log_file: Optional[Path] = None

    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        config = configparser.ConfigParser()
        config.read(config_path)
        
        return cls(
            source_dir=Path(config['DEFAULT']['source_dir']),
            destination_dir=Path(config['DEFAULT']['destination_dir']),
            debug_level=config['DEFAULT']['debug_level'],
            find_regex=config['url_translate']['find_regex'],
            from_regex=config['url_translate']['from_regex'],
            to_regex_replace=config['url_translate']['to_regex_replace'],
            style_mappings={
                config['style_translate']['from']: config['style_translate']['to']
            },
            log_file=Path(config['DEFAULT'].get('log_file', 'word_docx_morph.log'))
        )

    def validate(self) -> None:
        if not self.source_dir.exists():
            raise ValueError(f"Source directory does not exist: {self.source_dir}")
        if not self.destination_dir.parent.exists():
            raise ValueError(f"Destination directory parent does not exist: {self.destination_dir.parent}") 