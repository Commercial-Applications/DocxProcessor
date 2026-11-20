import re
from pathlib import Path
from unittest.mock import Mock

import pytest
from docx import Document

from docx_processor.config import AppConfig, RuntimeConfig, TransformConfig, RegexTransform
from docx_processor.processors import DocumentProcessor
from docx_processor.processors.docx_indexer import DocxIndexer


@pytest.fixture
def mock_logger():
    logger = Mock()
    logger.extra = {}
    logger.logger = Mock()
    return logger


@pytest.fixture
def test_doc_path():
    return Path("data/MocWordDoc.docx")


@pytest.fixture
def mock_config():
    runtime_config = RuntimeConfig(
        source_dir=Path("tests/input"),
        destination_dir=Path("tests/output"),
        log_file=Path("tests/test.log"),
        log_level="INFO",
        workers=1,
        sync_mode=True,
        find_only=False,
        verbose=0,
    )
    transform_config = TransformConfig(
        url_transforms=[
            RegexTransform(
                from_pattern=r"https://testcompany\.com/Test-(\d+)", to_pattern="https://newcompany.com/page-\\1"
            )
        ],
        text_transforms=[RegexTransform(from_pattern=r"FindMe\d", to_pattern="Found")],
        style_transforms=[],
        drop_matches=[],
    )

    return AppConfig(transform=transform_config, runtime=runtime_config)


class TestDocumentProcessor:
    def test_url_transformation_count(self, mock_config, mock_logger, test_doc_path):
        """
        Test that all testcompany.com URLs are found and transformed.
        """
        processor = DocumentProcessor(mock_config, mock_logger)
        doc = Document(test_doc_path)

        # Create document index first
        doc_index = DocxIndexer(doc, mock_logger)

        # Process document
        processor.transform_urls(doc, doc_index)

        # Count transformed URLs in relationships
        transformed_count = 0
        for rel in doc.part.rels.values():
            if "newcompany.com" in rel.target_ref:
                transformed_count += 1

        assert transformed_count == 25

    def test_mailto_links_preserved(self, mock_config, mock_logger, test_doc_path):
        processor = DocumentProcessor(mock_config, mock_logger)
        doc = Document(test_doc_path)

        # Create document index
        doc_index = DocxIndexer(doc, mock_logger)

        # Store original mailto links
        original_mailtos = []
        for rel in doc.part.rels.values():
            if rel.target_ref.startswith("mailto:"):
                original_mailtos.append(rel.target_ref)

        # Process document
        processor.transform_urls(doc, doc_index)

        # Check mailtos are unchanged
        for rel in doc.part.rels.values():
            if rel.target_ref.startswith("mailto:"):
                assert rel.target_ref in original_mailtos


def _paragraph_with_runs(*texts):
    doc = Document()
    para = doc.add_paragraph()
    for text in texts:
        para.add_run(text)
    return doc, para


class TestTextReplacement:
    def test_replace_within_single_run(self):
        _, para = _paragraph_with_runs("Welcome to South32 today")
        count = DocumentProcessor._replace_in_runs(para.runs, re.compile(r"South\s?32"), "GM3")
        assert count == 1
        assert para.text == "Welcome to GM3 today"

    def test_replace_spanning_runs_keeps_first_run_formatting(self):
        _, para = _paragraph_with_runs("Welcome to Sou", "th", "32 today")
        para.runs[0].bold = True
        count = DocumentProcessor._replace_in_runs(para.runs, re.compile(r"South\s?32"), "GM3")
        assert count == 1
        assert para.text == "Welcome to GM3 today"
        assert [r.text for r in para.runs] == ["Welcome to GM3", "", " today"]
        assert para.runs[0].bold is True

    def test_replace_multiple_matches_and_backreferences(self):
        _, para = _paragraph_with_runs("Test-1 and ", "Test-", "22 end")
        count = DocumentProcessor._replace_in_runs(para.runs, re.compile(r"Test-(\d+)"), r"page-\1")
        assert count == 2
        assert para.text == "page-1 and page-22 end"

    def test_transform_text_modifies_only_in_modify_mode(self, mock_config, mock_logger):
        doc = Document()
        doc.add_paragraph("Find FindMe1 here")
        doc.add_paragraph("No match")

        mock_config.runtime.find_only = True
        DocumentProcessor(mock_config, mock_logger).transform_text(
            doc, DocxIndexer(doc, mock_logger), mock_config.transform.text_transforms
        )
        assert doc.paragraphs[0].text == "Find FindMe1 here"

        mock_config.runtime.find_only = False
        DocumentProcessor(mock_config, mock_logger).transform_text(
            doc, DocxIndexer(doc, mock_logger), mock_config.transform.text_transforms
        )
        assert doc.paragraphs[0].text == "Find Found here"
        assert doc.paragraphs[1].text == "No match"

    def test_drop_matches_are_not_replaced(self, mock_config, mock_logger):
        doc = Document()
        doc.add_paragraph("Changelog: FindMe1 replaced")
        mock_config.transform.drop_matches = ["changelog:"]
        DocumentProcessor(mock_config, mock_logger).transform_text(
            doc, DocxIndexer(doc, mock_logger), mock_config.transform.text_transforms
        )
        assert doc.paragraphs[0].text == "Changelog: FindMe1 replaced"


class TestStylesAndSections:
    def test_style_rename(self, mock_config, mock_logger):
        doc = Document()
        mock_config.transform.style_transforms = [RegexTransform(from_pattern="Normal", to_pattern="Body GM3")]
        DocumentProcessor(mock_config, mock_logger).transform_styles(doc)
        assert "Body GM3" in [s.name for s in doc.styles]
        assert "Normal" not in [s.name for s in doc.styles]

    def test_transform_urls_does_not_add_headers_or_footers(self, mock_config, mock_logger):
        doc = Document()
        doc.add_paragraph("No headers here")
        DocumentProcessor(mock_config, mock_logger).transform_urls(doc, DocxIndexer(doc, mock_logger))
        section = doc.sections[0]
        assert section.header.is_linked_to_previous
        assert section.footer.is_linked_to_previous

    def test_process_document_reports_failure(self, mock_config, mock_logger, tmp_path):
        bad = tmp_path / "broken.docx"
        bad.write_text("not a docx")
        result = DocumentProcessor(mock_config, mock_logger).process_document(bad, tmp_path / "out.docx")
        assert result is False
