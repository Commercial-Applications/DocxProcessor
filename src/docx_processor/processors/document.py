import logging
import re
import unicodedata
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from .docx_indexer import DocxIndexer

W_P = qn("w:p")
W_TBL = qn("w:tbl")
W_TR = qn("w:tr")
W_TC = qn("w:tc")
W_SDT = qn("w:sdt")
W_SDT_CONTENT = qn("w:sdtContent")
W_TXBX_CONTENT = qn("w:txbxContent")
W_HYPERLINK = qn("w:hyperlink")
# Not in python-docx's namespace map. Word stores a text box twice: a DrawingML copy in
# mc:Choice and a VML copy in mc:Fallback for older readers. Both are updated; only one is logged.
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
W_R = qn("w:r")


class DocumentProcessor:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.url_patterns = [
            (re.compile(transform.from_pattern, re.IGNORECASE), transform.to_pattern)
            for transform in self.config.transform.url_transforms
        ]
        # Normalised once here rather than for every paragraph.
        self.drop_matches = [
            unicodedata.normalize("NFKC", pattern.strip()).lower() for pattern in self.config.transform.drop_matches
        ]
        # Debug messages below build strings from document text; skip that work unless DEBUG is on.
        self._debug = bool(self.logger.isEnabledFor(logging.DEBUG))
        self.logger.extra.update(
            {"location": "", "section": "", "document_name": "", "document_full_path": "", "module": __name__}
        )

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _iter_paragraphs(container) -> Iterator[Tuple[Paragraph, str, bool]]:
        """Yield ``(paragraph, table_label, quiet)`` for every paragraph in document order.

        Covers body paragraphs, tables (including nested tables), content controls (``w:sdt``)
        and text boxes. ``table_label`` is "" outside tables, otherwise "<table>|<row>"; nested
        tables are numbered "<outer>.<n>", tables in text boxes "textbox.<n>". ``quiet`` is True
        for the VML fallback copy of a text box: it is updated but not logged, so each match is
        reported once.

        Walks the XML directly, so each cell is visited once (a horizontally merged cell is a
        single ``w:tc``), unlike python-docx's ``row.cells`` which repeats merged cells.
        """
        parent = getattr(container, "_body", container)  # Document -> its body; header/footer as-is

        def unwrap(element, tag):
            """Children with ``tag``, looking through content controls that wrap them."""
            for child in element.iterchildren():
                if child.tag == tag:
                    yield child
                elif child.tag == W_SDT:
                    content = child.find(W_SDT_CONTENT)
                    if content is not None:
                        yield from unwrap(content, tag)

        def text_boxes(p, label: str, quiet: bool):
            for box in p.iter(W_TXBX_CONTENT):
                # Text boxes nested inside another text box are reached when that box is walked.
                ancestor, nested, fallback = box.getparent(), False, quiet
                while ancestor is not None and ancestor is not p:
                    if ancestor.tag == W_TXBX_CONTENT:
                        nested = True
                        break
                    if ancestor.tag == MC_FALLBACK:
                        fallback = True
                    ancestor = ancestor.getparent()
                if not nested:
                    yield from walk_block(box, label, "textbox", fallback)

        def walk_block(element, label: str, table_prefix: str, quiet: bool, counter=None):
            counter = counter if counter is not None else [0]
            for child in element.iterchildren():
                if child.tag == W_P:
                    yield Paragraph(child, parent), label, quiet
                    yield from text_boxes(child, label, quiet)
                elif child.tag == W_TBL:
                    counter[0] += 1
                    table_id = f"{table_prefix}.{counter[0]}" if table_prefix else str(counter[0])
                    for row_no, row in enumerate(unwrap(child, W_TR), 1):
                        for cell in unwrap(row, W_TC):
                            yield from walk_block(cell, f"{table_id}|{row_no}", table_id, quiet)
                elif child.tag == W_SDT:  # block-level content control: walk its content in place
                    content = child.find(W_SDT_CONTENT)
                    if content is not None:
                        yield from walk_block(content, label, table_prefix, quiet, counter)

        yield from walk_block(parent._element, "", "", False)

    @staticmethod
    def _headers_footers(doc: Document):
        """Yield ``(label, header_or_footer)`` for every defined header/footer in every section.

        Linked ones are skipped: they reuse a prior section's part (already processed), and for the
        first section touching an undefined header/footer makes python-docx add an empty one.
        """
        for section in doc.sections:
            for label, header_footer in (
                ("Header", section.header),
                ("First Page Header", section.first_page_header),
                ("Even Page Header", section.even_page_header),
                ("Footer", section.footer),
                ("First Page Footer", section.first_page_footer),
                ("Even Page Footer", section.even_page_footer),
            ):
                if not header_footer.is_linked_to_previous:
                    yield label, header_footer

    @staticmethod
    def _text_runs(paragraph: Paragraph) -> List[Run]:
        """The paragraph's text runs, including runs inside inline content controls, in document order.

        Walks the children directly (equivalent to the XPath ``./w:r | ./w:sdt/w:sdtContent/w:r``,
        but much cheaper per paragraph).
        """
        runs = []
        for child in paragraph._p.iterchildren():
            if child.tag == W_R:
                runs.append(Run(child, paragraph))
            elif child.tag == W_SDT:
                content = child.find(W_SDT_CONTENT)
                if content is not None:
                    runs.extend(Run(r, paragraph) for r in content.iterchildren(W_R))
        return runs

    @staticmethod
    def _is_in_table(paragraph: Optional[Paragraph]) -> bool:
        """True if the paragraph is inside a table cell."""
        return paragraph is not None and next(paragraph._p.iterancestors(W_TC), None) is not None

    def _set_location(self, paragraph: Optional[Paragraph], doc_index, in_table: bool) -> None:
        if in_table:
            self.logger.extra["location"] = "Table"
        else:
            self.logger.extra["location"] = doc_index.find_closest_heading_above(paragraph) or ""

    def _log_match(self, message: str) -> None:
        self.logger.extra["match"] = "True"
        self.logger.info(message)
        self.logger.extra["match"] = "False"

    # ------------------------------------------------------------------ URLs

    def _rel_hyperlinks(self, element, doc_index) -> None:
        """Rewrite hyperlink targets (relationships) in one part of the document."""
        self.logger.extra.update({"module": "rel_hyperlinks", "task": "rel_URLs"})
        part = element.part
        in_body = part is doc_index.doc.part

        for rel_id, rel in part.rels.items():
            if rel.reltype != RT.HYPERLINK:
                continue
            original_url = url = rel.target_ref
            located = in_table = False
            # Rules are applied in order, each to the result of the previous one.
            for pattern, replacement in self.url_patterns:
                if not pattern.search(url):
                    continue
                if not located:
                    # rIds are scoped per part; the index only covers the main document body,
                    # so a header/footer rId must not be looked up there (it could hit a body link).
                    para = doc_index.find_paragraph_by_rId(rel_id) if in_body else None
                    in_table = self._is_in_table(para)
                    self._set_location(para, doc_index, in_table)
                    located = True
                new_url = pattern.sub(replacement, url)
                self._log_match(f"{'TABLE: ' if in_table else ''}{url} -> {new_url}")
                url = new_url
            if url != original_url:
                rel._target = url

    def _para_hyperlinks(self, element, doc_index) -> None:
        """Rewrite the visible text of hyperlinks (body and tables) in one part of the document."""
        self.logger.extra.update({"module": "para_hyperlinks", "task": "para_URLs"})
        for para, table_label, quiet in self._iter_paragraphs(element):
            if para._p.find(W_HYPERLINK) is None:  # fast C-level check before python-docx objects
                continue
            for hyperlink in para.hyperlinks:
                for run in hyperlink.runs:
                    original_text = text = run.text
                    located = False
                    for pattern, replacement in self.url_patterns:
                        if not pattern.search(text):
                            continue
                        new_text = pattern.sub(replacement, text)
                        if not quiet:
                            if not located:
                                self.logger.extra["table_row"] = table_label
                                self._set_location(para, doc_index, bool(table_label))
                                located = True
                            self._log_match(f"{text} -> {new_text}")
                        text = new_text
                    if text != original_text:
                        run.text = text
        self.logger.extra["table_row"] = ""

    def transform_urls(self, doc: Document, doc_index) -> None:
        """
        Modify URLs in the document.
        There are 2 types or URL's Relationship and Paragraph
        There are 3 Broad locations Headers(multiple), Footers(multiple) and Body
        """
        # Process body text
        self.logger.extra["section"] = "Body"
        self._rel_hyperlinks(doc, doc_index)  # Type A
        self._para_hyperlinks(doc, doc_index)  # Type B

        # Headers and footers (default, first-page and even-page variants)
        for label, header_footer in self._headers_footers(doc):
            self.logger.extra["section"] = label
            self._rel_hyperlinks(header_footer, doc_index)  # Type A
            self._para_hyperlinks(header_footer, doc_index)  # Type B

    # ------------------------------------------------------------------ styles

    def transform_styles(self, doc: Document) -> None:
        """Change style names according to configuration."""
        self.logger.extra.update(
            {
                "section": "Whole Document",
                "module": "transform_styles",
            }
        )

        for transform in self.config.transform.style_transforms:
            for style in doc.styles:
                if style.name == transform.from_pattern:
                    style.name = transform.to_pattern
                    self._log_match(
                        f"Style {transform.from_pattern} found. Renaming: "
                        f"{transform.from_pattern} → {transform.to_pattern}"
                    )

    # ------------------------------------------------------------------ text

    def _should_drop_match(self, text: str) -> bool:
        """Check if text contains any drop_matches phrase (case and Unicode-form insensitive)."""
        if not self.drop_matches:
            return False
        normalized = unicodedata.normalize("NFKC", text.strip()).lower()
        for pattern in self.drop_matches:
            if pattern in normalized:
                if self._debug:
                    self.logger.debug(f"Dropping match for text: '{normalized[:50]}...'")
                return True
        return False

    def transform_text(self, element, doc_index, transforms, section: str = "Body") -> None:
        """Find (and in --modify mode replace) text patterns in one part: the body or a header/footer."""
        self.logger.extra.update({"section": section, "module": "transform_text"})
        patterns = [(re.compile(t.from_pattern), t.to_pattern, t.from_pattern) for t in transforms]
        modify = not self.config.runtime.find_only

        for para, table_label, quiet in self._iter_paragraphs(element):
            self._process_text_paragraph(para, table_label, doc_index, patterns, modify, quiet)

        self.logger.extra["table_row"] = ""

    def _process_text_paragraph(
        self, para, table_label: str, doc_index, patterns, modify: bool, quiet: bool = False
    ) -> bool:
        """Log (unless ``quiet``) and, when ``modify``, replace pattern matches in one paragraph."""
        runs = self._text_runs(para)
        # Read each run's text once: every run.text access is an XPath query in python-docx.
        texts = [run.text for run in runs]
        para_text = "".join(texts)
        if not para_text:
            return False
        if self._debug:
            self.logger.debug(f"Paragraph Text: {para_text}")
        if self._should_drop_match(para_text):
            return False

        found_match = False
        for pattern, replacement, source in patterns:
            matches = len(pattern.findall(para_text))
            if not matches:
                continue
            if quiet:  # duplicate (fallback) copy of a text box: keep it in sync, don't report it twice
                if modify:
                    self._replace_in_runs(runs, pattern, replacement, texts)
                    para_text = "".join(texts)
                continue
            if not found_match:
                self.logger.extra["table_row"] = table_label
                self._set_location(para, doc_index, bool(table_label))
                found_match = True

            trunc_para_text = (para_text[:47] + "...") if len(para_text) > 50 else para_text
            self.logger.extra["match"] = "True"
            self.logger.info(
                f"Match: {matches} {'matches' if matches > 1 else 'match'} "
                f"for '{source}' at paragraph: '{trunc_para_text}'"
            )
            if modify:
                replaced = self._replace_in_runs(runs, pattern, replacement, texts)
                para_text = "".join(texts)
                self.logger.info(f"Replaced {replaced} with '{replacement}'")
            self.logger.extra["match"] = "False"

        return found_match

    @staticmethod
    def _replace_in_runs(runs, pattern, replacement, texts: Optional[List[str]] = None) -> int:
        """Replace regex matches in a paragraph's runs, preserving run formatting where possible.

        A match may span several runs (Word splits text on formatting, spell-check, edits, ...).
        The replacement text is placed in the run where the match starts, keeping that run's
        formatting, and the matched text is removed from the following runs. Returns the
        number of replacements made.

        ``texts`` is an optional cache of the runs' current text; it is kept up to date in place.
        """
        if texts is None:
            texts = [run.text for run in runs]
        full_text = "".join(texts)
        matches = [m for m in pattern.finditer(full_text) if m.end() > m.start()]

        # Work backwards so the offsets of earlier matches stay valid as text changes.
        for match in reversed(matches):
            start, end = match.span()
            new_text = match.expand(replacement)

            run_start = 0
            for i, run in enumerate(runs):
                text = texts[i]
                run_end = run_start + len(text)
                if run_end > start and run_start < end:
                    local_start = max(start - run_start, 0)
                    local_end = min(end - run_start, len(text))
                    if run_start <= start:
                        # First run of the match receives the replacement text.
                        updated = text[:local_start] + new_text + text[local_end:]
                    else:
                        updated = text[local_end:]
                    # Only write runs whose text changes: python-docx's run.text setter removes all
                    # other run content, e.g. the picture or text box in an empty run inside a match.
                    if updated != text:
                        run.text = updated
                        texts[i] = updated
                run_start = run_end
                if run_start >= end:
                    break

        return len(matches)

    # ------------------------------------------------------------------ entry point

    def process_document(self, input_path: Path, output_path: Path) -> bool:
        """Process a single document. Returns True on success, False if it failed."""
        # Reset all per-document context so nothing from the previous document leaks into this one's log lines.
        self.logger.extra.update(
            {
                "document_name": input_path.name,
                "document_full_path": str(input_path.parent),
                "section": "NA",
                "module": "process_document",
                "location": "",
                "table_row": "",
                "task": "Open",
                "match": "False",
            }
        )
        transforms = self.config.transform

        try:
            doc = Document(str(input_path))
            self.logger.extra.update({"section": "NA", "module": "process_document"})

            # The index is only needed to locate URL and text matches.
            doc_index = (
                DocxIndexer(doc, self.logger) if (transforms.url_transforms or transforms.text_transforms) else None
            )

            if transforms.url_transforms:
                self.logger.extra["task"] = "hyperlinks"
                self.logger.debug("Starting URL Identification")
                self.transform_urls(doc, doc_index)

            if transforms.style_transforms:
                self.logger.extra["task"] = "Styles"
                self.logger.debug("Starting Style Identification")
                self.transform_styles(doc)

            if transforms.text_transforms:
                self.logger.extra["task"] = "Text"
                self.logger.debug("Starting Text Identification")
                self.transform_text(doc, doc_index, transforms.text_transforms)
                for label, header_footer in self._headers_footers(doc):
                    self.transform_text(header_footer, doc_index, transforms.text_transforms, section=label)

            # Save The Document
            if not self.config.runtime.find_only:
                doc.save(str(output_path))
                self.logger.extra.update({"section": "NA", "task": "Finish", "module": "process_document"})
                self.logger.debug(f"Document saved: {output_path}")

            return True

        except Exception as e:
            self.logger.extra["task"] = "ERROR"
            # Full message (it used to be cut at the first ":", e.g. the one in "C:\"); traceback when debugging.
            self.logger.error(f"Failed to process {input_path}: {type(e).__name__}: {e}", exc_info=self._debug)
            return False
