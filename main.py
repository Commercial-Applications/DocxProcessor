# Proof of concept
import logging

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from pathlib import Path
from typing import Callable
from config import Config
from logger import DocxLogger, ContextLoggerAdapter
import re

import zipfile
from lxml import etree

def non_rel_hyperlinks(logger, file_path: Path) -> None:
    # Logs as an Error
    with zipfile.ZipFile(file_path) as docx:
        xml_content = docx.read('word/document.xml')
    tree = etree.fromstring(xml_content)
    # Namespaces
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    # Find all field code runs
    instr_texts = tree.xpath('//w:instrText', namespaces=ns)

    for instr in instr_texts:
        if instr.text and 'HYPERLINK' in instr.text:
            # Extract the URL inside the HYPERLINK field code
            parts = instr.text.split('"')
            if len(parts) >= 2:
                logger.extra['section'] = 'XML'
                logger.error(f"Non-Rel URL: {parts[1]}")  # URL is typically the first quoted string


class DocxProcessor:
    def __init__(self, config: Config, logger):
        self.config = config
        self.logger = logger
        self.url_pattern = re.compile(self.config.find_regex, re.IGNORECASE)

    def rel_hyperlinks(self, element: Document, modify_func: Callable[[str], str]) -> None:
        """Process a section of the document for URL modifications."""
        # Process hyperlinks in relationships
        if hasattr(element.part, 'rels'):
            for rel_id, rel in element.part.rels.items():
                if rel.reltype == RT.HYPERLINK:
                    original_url = rel.target_ref
                    if self.url_pattern.search(original_url):
                        new_url = modify_func(original_url)
                        self.logger.debug(f"{rel.target_ref} -> {new_url}")
                        rel._target = new_url

    def para_hyperlinks(self, element: Document, modify_func: Callable[[str], str]) -> None:
        for para in element.paragraphs:
            for hyperlink in para.hyperlinks:
                for runs in hyperlink.runs:
                    original_url = runs.text
                    if self.url_pattern.search(original_url):
                        new_url = modify_func(original_url)
                        self.logger.debug(f"{runs.text} -> {new_url}")
                        runs.text = new_url

    def modify_urls_in_docx(self, doc: Document, file_path: Path) -> None:
        """Modify URLs in the document."""
        # Process body text
        self.logger.extra['section'] = 'Body'
        self.rel_hyperlinks(doc, self.url_replace_regex)
        self.para_hyperlinks(doc, self.url_replace_regex)

        # Process headers and footers
        for idx, section in enumerate(doc.sections):
            self.logger.extra['section'] = 'Header'
            self.rel_hyperlinks(section.header, self.url_replace_regex)
            self.para_hyperlinks(section.header, self.url_replace_regex)

            self.logger.extra['section'] = 'Footer'
            self.rel_hyperlinks(section.footer, self.url_replace_regex)

    def url_replace_regex(self, original_url: str) -> str:
        """Replace URLs according to the configured pattern."""
        return re.sub(
            self.config.from_regex,
            self.config.to_regex_replace,
            original_url,
            flags=re.IGNORECASE
        )

    def change_style_name(self, doc: Document, input_path) -> None:
        """Change style names according to configuration."""
        self.logger.debug(f"Starting Style modification")
        for old_style, new_style in self.config.style_mappings.items():
            for style in doc.styles:
                if style.name == old_style:
                    style.name = new_style
                    self.logger.info(f"Table Style {old_style} Found.. Converting, {old_style} → {new_style}")

    def process_document(self, input_path: Path, output_path: Path) -> None:
        """Process a single document."""
        try:
            doc = Document(str(input_path))
            self.logger.extra['document_name'] = input_path.name
            self.logger.extra['document_full_path'] = input_path.parent
            self.logger.extra['task'] = 'Process Document'
            self.logger.debug("START")

            # Check for non standard Hyperlinks and Log
            self.logger.extra['task'] = 'URLS'
            non_rel_hyperlinks(self.logger,input_path)

            # Modify Relationship URLS
            self.logger.extra['task'] = 'URLS'
            self.modify_urls_in_docx(doc, input_path)

            # Rename Styles
            self.logger.extra['task'] = 'STYLE'
            self.change_style_name(doc, input_path)

            # Save The Document
            doc.save(str(output_path))
            self.logger.extra['task'] = 'END'
            self.logger.debug(f"Document saved: {output_path}")
        except Exception as e:
            self.logger.exception(f"Failed to process {input_path} with error: {e}")

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

    # Initialize Custom logger
    cust_logger = DocxLogger(config.log_file,logging.DEBUG)

    # Initialize Logger with Adapter
    logger = ContextLoggerAdapter(
        cust_logger.logger,
  {}  # Default section
    )
    # Process documents
    processor = DocxProcessor(config, logger)
    processor.process_all_docx()

if __name__ == "__main__":
    main()
