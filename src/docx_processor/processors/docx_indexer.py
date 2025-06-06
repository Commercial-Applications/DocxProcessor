from docx import Document
from docx.text.paragraph import Paragraph
from typing import Dict, List, Optional, Tuple

class DocxIndexer:
  def __init__(self, doc: Document):
    self.doc = doc
    self.rId_to_paragraph: Dict[str, Paragraph] = {}
    self.paragraph_index: Dict[Paragraph, int] = {}
    self.heading_paragraphs: List[Tuple[Paragraph, int]] = []
    self._build_index()

  def _build_index(self):
    """
    Builds the following indexes:
    - rId_to_paragraph: Maps rId to the corresponding Paragraph object.
    - paragraph_index: Maps Paragraph object to its index in the document.
    - heading_paragraphs: List of all heading paragraphs in the document.
    """
    for i, para in enumerate(self.doc.paragraphs):
      self.paragraph_index[para] = i
      if para.style.name.startswith("Heading"):
        try:
          heading_level = int(para.style.name[7:])  # Extract heading level (e.g., "Heading 1" -> 1)
        except ValueError:
          heading_level = 0  # Default to 0 if extraction fails
        self.heading_paragraphs.append((para, heading_level))

      for element in para._element.iter():
        if element.tag.endswith('hyperlink'):
          rId_value = element.get(f'{{{element.nsmap["r"]}}}id')
          if rId_value:
            self.rId_to_paragraph[rId_value] = para


  def find_paragraph_by_rId(self, rId: str) -> Optional[Paragraph]:
    """
    Retrieves a Paragraph object by its rId from the index.
    """
    return self.rId_to_paragraph.get(rId)


  def find_closest_heading_above(self, paragraph: Paragraph) -> Optional[Tuple[Paragraph, int]]:
    """
    Finds the closest heading paragraph above a given paragraph using the pre-built index.
    Returns a tuple (Paragraph, heading_level) or None if no heading is found.
    """
    paragraph_index = self.paragraph_index.get(paragraph, -1)
    if paragraph_index == -1:
      # paragraph was not in the index (should not happen)
      return None

    closest_heading = None
    closest_heading_level = None

    for heading, level in reversed(self.heading_paragraphs):
      if self.paragraph_index[heading] < paragraph_index:
        return f"H{level} {heading.text}"
    return None


