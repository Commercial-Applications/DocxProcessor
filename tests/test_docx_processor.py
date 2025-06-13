from pathlib import Path
from unittest.mock import Mock

import pytest
from docx import Document

from src.docx_processor.config import AppConfig, RuntimeConfig, TransformConfig, RegexTransform
from src.docx_processor.processors import DocumentProcessor
from src.docx_processor.processors.docx_indexer import DocxIndexer


@pytest.fixture
def mock_logger():
    logger = Mock()
    logger.extra = {}
    logger.logger = Mock()
    return logger


@pytest.fixture
def test_doc_path():
    return Path("mocs/MocWordDoc.docx")


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
        verbose=0
    )
    transform_config = TransformConfig(
        url_transforms=[
            RegexTransform(
                from_pattern=r"https://testcompany\.com/Test-(\d+)",
                to_pattern="https://newcompany.com/page-\\1"
            )
        ],
        text_transforms=[
            RegexTransform(
                from_pattern=r"FindMe\d",
                to_pattern="Found"
            )
        ],
        style_transforms=[]
    )

    return AppConfig(
        transform=transform_config,
        runtime=runtime_config
    )


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
