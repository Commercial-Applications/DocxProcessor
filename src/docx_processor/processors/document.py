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
        #TODO: Loop through Multiple Regexs - Set to the first at the min.

        # Initialize base logger context that will be constant for this document processor
        self.logger.extra.update({
            'location': '',
            'section': '',
            'document_name': '',
            'document_full_path': '',
            'module': __name__
        })
        self.current_heading = None

    def _track_heading(self, paragraph):
        """Track the current heading level if paragraph is a heading."""
        try:
            # Reset current heading at start of new document
            if not hasattr(self, 'current_heading'):
                self.current_heading = None
                self.logger.extra['location'] = ''

            if (hasattr(paragraph, 'style') and
                    hasattr(paragraph.style, 'name') and
                    paragraph.style.name.startswith('Heading')):

                heading_text = ''
                for run in paragraph.runs:
                    if hasattr(run, 'text'):
                        heading_text += run.text

                heading_text = heading_text.strip()
                if heading_text:  # Only update if we have text content
                    level = paragraph.style.name.split()[-1] if len(paragraph.style.name.split()) > 1 else ''
                    truncated_text = heading_text[:50] + ('...' if len(heading_text) > 50 else '')
                    self.current_heading = f"H{level}: {truncated_text}"
                    # Reset and update logger extra
                    self.logger.extra['location'] = self.current_heading

        except Exception as e:
            self.logger.debug(f"Heading tracking error: {str(e)}")

    def _rel_hyperlinks(self, element: Document, modify_func: Callable[[str], str]) -> None:
        """Process a section of the document for URL modifications."""
        self.logger.extra.update({
            'module': 'rel_hyperlinks',
            'task': 'rel_URLs'
        })
        if hasattr(element.part, 'rels'):
            # Track the current paragraph we're in
            for paragraph in element.paragraphs:
                # Update heading context for this paragraph
                self._track_heading(paragraph)
                # Look for hyperlinks in this paragraph's runs
                for run in paragraph.runs:
                    if hasattr(run, '_r'):
                        # Find hyperlink elements
                        hyperlink_element = run._r.getparent()
                        if hyperlink_element is not None and hyperlink_element.tag.endswith('hyperlink'):
                            # Get the relationship ID
                            rel_id = hyperlink_element.get(
                                '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                            if rel_id and rel_id in element.part.rels:
                                rel = element.part.rels[rel_id]
                                if rel.reltype == RT.HYPERLINK:
                                    original_url = rel.target_ref
                                    if self.url_pattern.search(original_url):
                                        new_url = modify_func(original_url)
                                        self.logger.extra['match'] = 'True'
                                        self.logger.info(f"{rel.target_ref} -> {new_url}")
                                        self.logger.extra['match'] = 'False'
                                        rel._target = new_url

    def _para_hyperlinks(self, element: Document, modify_func: Callable[[str], str]) -> None:
        self.logger.extra.update({
            'module': 'para_hyperlinks',
            'task': 'para_URLs'
            })
        for para in element.paragraphs:
            self._track_heading(para)
            for hyperlink in para.hyperlinks:
                for runs in hyperlink.runs:
                    original_url = runs.text
                    if self.url_pattern.search(original_url):
                        new_url = modify_func(original_url)
                        self.logger.extra['match'] = 'True'
                        self.logger.debug(f"{runs.text} -> {new_url}")
                        self.logger.extra['match'] = 'False'
                        runs.text = new_url

    def transform_urls(self, doc: Document) -> None:
        """
        Modify URLs in the document.
        There are 2 types or URL's Relationship and Paragraph
        There are 3 Broad locations Headers(multiple), Footers(multiple) and Body
        TODO: Add Tables
        """
        # Process body text
        self.logger.extra['section'] = 'Body'
        self._rel_hyperlinks(doc, self._url_replace_regex) # Type A
        self._para_hyperlinks(doc, self._url_replace_regex) # Type B

        # Process headers and footers
        for idx, section in enumerate(doc.sections):
            self.logger.extra['section'] = 'Header'
            self._rel_hyperlinks(section.header, self._url_replace_regex) # Type A
            self._para_hyperlinks(section.header, self._url_replace_regex) # Type A

            self.logger.extra['section'] = 'Footer'
            self._rel_hyperlinks(section.footer, self._url_replace_regex) # Type A

    def _url_replace_regex(self, original_url: str) -> str:
        """Replace URLs according to the configured pattern."""
        from_domain  = self.config.transform.url_transforms[0].from_pattern
        to_domain = self.config.transform.url_transforms[0].to_pattern

        def www_addition(match):
            prefix = match.group(1) or ""
            return prefix + to_domain

        return re.sub(
            from_domain,
            www_addition,
            original_url,
            flags=re.IGNORECASE
        )

    def transform_styles(self, doc: Document) -> None:
        """Change style names according to configuration."""
        self.logger.extra.update({
            'section': 'Whole Document',
            'module': 'transform_styles',
        })

        for transform in self.config.transform.style_transforms:
            for style in doc.styles:
                if style.name == transform.from_pattern:
                    #TODO: Logg and check if we are changing
                    style.name = transform.to_pattern
                    self.logger.extra['match'] = 'True'
                    self.logger.info(f"Table Style {transform.from_pattern} Found.. Converting, {transform.from_pattern} → {transform.new_pattern}")
                    self.logger.extra['match'] = 'False'

    def transform_text(self, doc: Document):
        return None
        # TODO: Add Text Transformation

    def process_document(self, input_path: Path, output_path: Path) -> None:
        """Process a single document."""
        self.logger.extra.update({
            'document_name': input_path.name,
            'document_full_path': str(input_path.parent)
        })

        try:
            doc = Document(str(input_path))
            self.logger.extra.update({
                'section': 'NA',
                'module': 'process_document'
            })
            self.logger.debug("START Document Processing")

            # Check for non standard Hyperlinks and Log
            self.logger.debug(f"Starting Non-Rel-URL Identification")
            non_rel_hyperlinks(self.logger, input_path)

            # TODO Several of these have to itterate Paragraphs so makes sense to do them in one block
            if self.config.transform.url_transforms:
                self.logger.debug(f"Starting URL modification")
                self.transform_urls(doc)

            if self.config.transform.style_transforms:
                self.logger.extra['task'] = 'Styles'
                self.logger.debug(f"Starting Style Identification")
                self.transform_styles(doc)

            if self.config.transform.text_transforms:
                self.logger.extra['task'] = 'Text'
                self.logger.debug(f"Starting Text Identification")
                self.transform_text(doc)

            # Save The Document
            if not self.config.runtime.find_only:
                doc.save(str(output_path))
                self.logger.extra.update({
                    'section': 'NA',
                    'task': 'Finish',
                    'module': 'process_document'
                })
                self.logger.debug(f"Document saved: {output_path}")

        except Exception as e:
            self.logger.extra['task'] = 'ERROR'
            self.logger.exception(f"Failed to process {input_path} with error: {e}")


