import re
from bisect import bisect_left
from typing import Dict, List, Optional

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

W_P = qn("w:p")
W_PPR = qn("w:pPr")
W_OUTLINE_LVL = qn("w:outlineLvl")
W_VAL = qn("w:val")
W_HYPERLINK = qn("w:hyperlink")
R_ID = qn("r:id")

BODY_TEXT_LEVEL = 9  # w:outlineLvl 9 means "body text" (not a heading)
HEADING_NAME = re.compile(r"(?i)^heading\s*(\d+)$")


def _outline_level(ppr) -> Optional[int]:
    """Heading level (1-9) from a w:pPr's w:outlineLvl; 0 for explicit body text; None if not set."""
    if ppr is None:
        return None
    outline = ppr.find(W_OUTLINE_LVL)
    if outline is None:
        return None
    try:
        value = int(outline.get(W_VAL))
    except (TypeError, ValueError):
        return None
    return value + 1 if 0 <= value < BODY_TEXT_LEVEL else 0


class DocxIndexer:
    """Index a document's body paragraphs for fast hyperlink and heading lookups.

    Paragraphs are indexed by their XML element in document order (tables included), in a single
    pass over the XML. This avoids python-docx's ``Paragraph.style`` property, whose lookup cost
    grows with the number of relationships (every hyperlink is one), and works for documents
    without Word's ``w14:paraId`` attributes.

    The element objects are held as dict keys, which keeps their lxml proxies alive; lxml then
    returns those same objects for later lookups, so identity-based lookups stay valid.
    """

    def __init__(self, doc: Document, logger):
        self.doc = doc
        self.logging = logger
        self.rId_to_paragraph: Dict[str, Paragraph] = {}
        self._position: Dict[object, int] = {}
        self._heading_positions: List[int] = []
        self._heading_labels: List[str] = []
        self._build_index()

    def _heading_levels(self) -> Dict[str, int]:
        """Map paragraph style id (as stored on each paragraph, e.g. "Heading1") to heading level.

        A style is a heading if it (or a style it is based on) sets an outline level, as Word's
        built-in headings do; this also catches custom heading styles with other names. Styles
        without an outline level fall back to a "Heading <n>" name (any case).
        """
        paragraph_styles = [s for s in self.doc.styles if s.type == WD_STYLE_TYPE.PARAGRAPH]

        def level_of(style, depth: int = 0) -> int:
            level = _outline_level(style.element.pPr)
            if level is not None:
                return level
            match = HEADING_NAME.match(style.name or "")
            if match:
                return int(match.group(1))
            base = style.base_style
            return level_of(base, depth + 1) if base is not None and depth < 20 else 0

        levels: Dict[str, int] = {}
        for style in paragraph_styles:
            level = level_of(style)
            if level:
                levels[style.style_id] = level
        return levels

    def _build_index(self) -> None:
        heading_levels = self._heading_levels()
        parent = self.doc._body
        for position, p in enumerate(self.doc.element.body.iter(W_P)):
            self._position[p] = position

            # A paragraph's own outline level overrides its style's.
            level = _outline_level(p.find(W_PPR))
            if level is None:
                level = heading_levels.get(p.style)
            if level:
                self._heading_positions.append(position)
                self._heading_labels.append(f"H{level} {Paragraph(p, parent).text}")

            for link in p.iter(W_HYPERLINK):
                r_id = link.get(R_ID)
                if r_id:
                    self.rId_to_paragraph[r_id] = Paragraph(p, parent)

    def find_paragraph_by_rId(self, rId: str) -> Optional[Paragraph]:
        """Return the paragraph containing the hyperlink with relationship id ``rId``."""
        return self.rId_to_paragraph.get(rId)

    def find_closest_heading_above(self, paragraph: Optional[Paragraph]) -> Optional[str]:
        """Return the nearest heading above ``paragraph`` as "H<level> <text>", or None."""
        if paragraph is None:
            return None
        position = self._position.get(paragraph._p)
        if position is None:
            return None
        k = bisect_left(self._heading_positions, position) - 1
        return self._heading_labels[k] if k >= 0 else None
