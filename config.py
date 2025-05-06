from dataclasses import dataclass
from pathlib import Path
import configparser
from typing import Optional

@dataclass
class Config:
    source_dir: Path
    destination_dir: Path
    url_pattern: str
    style_mappings: dict[str, str]
    log_file: Optional[Path] = None

    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        config = configparser.ConfigParser()
        config.read(config_path)
        
        return cls(
            source_dir=Path(config['DEFAULT']['source_dir']),
            destination_dir=Path(config['DEFAULT']['destination_dir']),
            url_pattern=config['url_translate']['from'],
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