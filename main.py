# Proof of concept

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from pathlib import Path
from typing import Callable, Pattern
from config import Config
from logger import DocxLogger
import re

class DocxProcessor:
    def __init__(self, config: Config, logger: DocxLogger):
        self.config = config
        self.logger = logger
        self.url_pattern = re.compile(r'https?://[^\s)]+', re.IGNORECASE)

    def process_section(self, name: str, element: Document, modify_func: Callable[[str], str]) -> None:
        """Process a section of the document for URL modifications."""
        self.logger.debug(f"Processing section: {name}")

        # Process hyperlinks in paragraphs
        for para_idx, para in enumerate(element.paragraphs):
            for hyperlink_idx, hyperlink in enumerate(para.hyperlinks):
                for run_idx, run in enumerate(hyperlink.runs):
                    if run.text and self.url_pattern.search(run.text):
                        original = run.text
                        new_url = modify_func(original)
                        self.logger.info(f"{name} Link-Text {para_idx}, Run {run_idx}: {original} → {new_url}")
                        run.clear()
                        run.add_text(new_url)

        # Process hyperlinks in relationships
        for rel in element.part.rels.values():
            if rel.reltype == RT.HYPERLINK:
                if self.url_pattern.search(rel.target_ref):
                    original = rel.target_ref
                    new_target = modify_func(original)
                    self.logger.info(f"{name} URL: {original} → {new_target}")
                    rel._target = new_target

    def modify_urls_in_docx(self, doc: Document, file_path: Path) -> None:
        """Modify URLs in the document."""
        self.logger.debug(f"Starting URL modification for: {file_path}")

        # Process body text
        self.process_section("Body", doc, self.url_replace_regex)

        # Process headers and footers
        for idx, section in enumerate(doc.sections):
            self.process_section(f"Header {idx}", section.header, self.url_replace_regex)
            self.process_section(f"Footer {idx}", section.footer, self.url_replace_regex)

    def url_replace_regex(self, original_url: str) -> str:
        """Replace URLs according to the configured pattern."""
        return re.sub(
            self.config.url_pattern,
            'gm3.au',
            original_url,
            flags=re.IGNORECASE
        )

    def change_style_name(self, doc: Document) -> None:
        """Change style names according to configuration."""
        for old_style, new_style in self.config.style_mappings.items():
            for style in doc.styles:
                if style.name == old_style:
                    style.name = new_style
                    self.logger.info(f"Table Style {old_style} Found.. Converting, {old_style} → {new_style}")

    def process_document(self, input_path: Path, output_path: Path) -> None:
        """Process a single document."""
        try:
            doc = Document(str(input_path))
            self.modify_urls_in_docx(doc, output_path)
            self.change_style_name(doc)
            doc.save(output_path)
            self.logger.debug(f"Document saved: {output_path}")
        except Exception as e:
            self.logger.exception(f"Failed to process {input_path}")

    def process_all_docx(self) -> None:
        """Process all documents in the source directory."""
        for input_path in self.config.source_dir.rglob("*.docx"):
            if input_path.name.startswith("~$"):  # Skip temporary Word files
                continue

            relative_path = input_path.relative_to(self.config.source_dir)
            output_path = self.config.destination_dir / relative_path

            # Ensure destination directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.process_document(input_path, output_path)

def main():
    # Load configuration
    config = Config.from_file('word_docx_morph.ini')
    config.validate()

    # Initialize logger
    logger = DocxLogger(config.log_file)

    # Process documents
    processor = DocxProcessor(config, logger)
    processor.process_all_docx()

if __name__ == "__main__":
    main()
