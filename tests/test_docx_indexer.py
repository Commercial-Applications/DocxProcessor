from unittest.mock import Mock

import pytest
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from docx_processor.processors.docx_indexer import DocxIndexer

W14_PARA_ID = "{http://schemas.microsoft.com/office/word/2010/wordml}paraId"


def add_hyperlink(paragraph, url, text):
    """Append an external hyperlink to a paragraph; returns its relationship id."""
    r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = text
    run.append(t)
    link.append(run)
    paragraph._p.append(link)
    return r_id


@pytest.fixture
def doc():
    d = Document()
    d.add_paragraph("Intro before any heading")  # 0
    d.add_heading("Chapter One", level=1)  # 1
    d.add_paragraph("Body under chapter one")  # 2
    d.add_heading("Section 1.1", level=2)  # 3
    link_para = d.add_paragraph("See ")  # 4
    d.link_rid = add_hyperlink(link_para, "https://example.com/a", "link")
    d.add_table(rows=1, cols=1).cell(0, 0).text = "In table"
    d.add_heading("Chapter Two", level=1)  # 5
    d.add_paragraph("Body under chapter two")  # 6
    return d


@pytest.fixture
def logger():
    return Mock()


def test_closest_heading_levels_and_text(doc, logger):
    index = DocxIndexer(doc, logger)
    paras = doc.paragraphs
    assert index.find_closest_heading_above(paras[2]) == "H1 Chapter One"
    assert index.find_closest_heading_above(paras[4]) == "H2 Section 1.1"
    assert index.find_closest_heading_above(paras[6]) == "H1 Chapter Two"


def test_no_heading_before_first_heading(doc, logger):
    assert DocxIndexer(doc, logger).find_closest_heading_above(doc.paragraphs[0]) is None


def test_heading_returns_previous_heading_not_itself(doc, logger):
    assert DocxIndexer(doc, logger).find_closest_heading_above(doc.paragraphs[3]) == "H1 Chapter One"


def test_table_paragraph_gets_heading_above_the_table(doc, logger):
    cell_para = doc.tables[0].cell(0, 0).paragraphs[0]
    assert DocxIndexer(doc, logger).find_closest_heading_above(cell_para) == "H2 Section 1.1"


def test_lookups_work_without_word_paragraph_ids(doc, logger):
    """Regression: documents not saved by Word have no w14:paraId; lookups must still be stable."""
    assert not any(p._p.get(W14_PARA_ID) for p in doc.paragraphs)
    index = DocxIndexer(doc, logger)
    # Fresh Paragraph objects on every access must still resolve, repeatedly.
    for _ in range(3):
        assert index.find_closest_heading_above(doc.paragraphs[2]) == "H1 Chapter One"


def test_find_paragraph_by_rid(doc, logger):
    index = DocxIndexer(doc, logger)
    assert index.find_paragraph_by_rId(doc.link_rid)._p is doc.paragraphs[4]._p
    assert index.find_paragraph_by_rId("rId-missing") is None


def test_unknown_or_missing_paragraph_returns_none(doc, logger):
    index = DocxIndexer(doc, logger)
    other = Document().add_paragraph("from another document")
    assert index.find_closest_heading_above(other) is None
    assert index.find_closest_heading_above(None) is None
