from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from pathlib import Path
from typing import Callable
from docx_processor.utils import non_rel_hyperlinks
import re


class DocumentProcessor:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.url_pattern = re.compile(self.config.transform.url_transforms[0].from_pattern, re.IGNORECASE)

    def rel_hyperlinks(self, element: Document, modify_func: Callable[[str], str]) -> None:
        """Process a section of the document for URL modifications."""
        # Process hyperlinks in relationships
        if hasattr(element.part, 'rels'):
            for rel_id, rel in element.part.rels.items():
                if rel.reltype == RT.HYPERLINK:
                    original_url = rel.target_ref

# TODO: This is redundant just replace it only will replace matches and it searches first
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
            self.config.transform.url_transforms[0].from_pattern,
            self.config.transform.url_transforms[0].to_pattern,
            original_url,
            flags=re.IGNORECASE
        )

    def change_style_name(self, doc: Document, input_path) -> None:
        """Change style names according to configuration."""
        self.logger.debug(f"Starting Style modification")
        for old_style, new_style in self.config.transform.style_transforms[0]:
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

            if self.config.runtime.find_only:
                # Modify Relationship URLS
                self.logger.extra['task'] = 'URLS'
                self.modify_urls_in_docx(doc, input_path)

            # Save The Document
            doc.save(str(output_path))
            self.logger.extra['task'] = 'END'
            self.logger.debug(f"Document saved: {output_path}")
        except Exception as e:
            self.logger.exception(f"Failed to process {input_path} with error: {e}")

