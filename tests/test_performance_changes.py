"""Tests for behaviour introduced with the indexer / text-pass / process-pool rework."""

import csv
import logging
import shutil
from pathlib import Path
from unittest.mock import Mock

import pytest
from docx import Document

from docx_processor.config import AppConfig, RegexTransform, RuntimeConfig, TransformConfig
from docx_processor.logger import ContextLoggerAdapter, setup_logger
from docx_processor.processors import BatchProcessor, DocumentProcessor
from docx_processor.processors.docx_indexer import DocxIndexer
from test_docx_indexer import add_hyperlink

DATA_DIR = Path(__file__).parent / "data"


def make_config(tmp_path, url=(), text=(), find_only=False, workers=1):
    return AppConfig(
        transform=TransformConfig(
            url_transforms=[RegexTransform(f, t) for f, t in url],
            text_transforms=[RegexTransform(f, t) for f, t in text],
            style_transforms=[],
            drop_matches=[],
        ),
        runtime=RuntimeConfig(
            source_dir=tmp_path / "in",
            destination_dir=tmp_path / "out",
            log_file=tmp_path / "run.log",
            log_level="INFO",
            workers=workers,
            sync_mode=workers == 1,
            find_only=find_only,
            verbose=0,
        ),
    )


@pytest.fixture
def mock_logger():
    logger = Mock()
    logger.extra = {}
    return logger


def match_logs(logger):
    return [c.args[0] for c in logger.info.call_args_list if str(c.args[0]).startswith("Match:")]


class TestUrls:
    def test_url_rules_are_applied_in_sequence(self, tmp_path, mock_logger):
        config = make_config(tmp_path, url=[(r"old\.example", "mid.example"), (r"mid\.example", "new.example")])
        doc = Document()
        r_id = add_hyperlink(doc.add_paragraph(), "https://old.example/page", "https://old.example/page")

        DocumentProcessor(config, mock_logger).transform_urls(doc, DocxIndexer(doc, mock_logger))

        assert doc.part.rels[r_id].target_ref == "https://new.example/page"
        assert doc.paragraphs[0].hyperlinks[0].runs[0].text == "https://new.example/page"

    def test_hyperlink_text_inside_table_is_updated(self, tmp_path, mock_logger):
        config = make_config(tmp_path, url=[(r"old\.example", "new.example")])
        doc = Document()
        cell_para = doc.add_table(rows=1, cols=1).cell(0, 0).paragraphs[0]
        add_hyperlink(cell_para, "https://old.example/x", "https://old.example/x")

        DocumentProcessor(config, mock_logger).transform_urls(doc, DocxIndexer(doc, mock_logger))

        assert doc.tables[0].cell(0, 0).paragraphs[0].hyperlinks[0].runs[0].text == "https://new.example/x"


class TestTables:
    def test_nested_table_text_is_replaced(self, tmp_path, mock_logger):
        config = make_config(tmp_path, text=[(r"FindMe\d", "Found")])
        doc = Document()
        outer = doc.add_table(rows=1, cols=1)
        outer.cell(0, 0).add_table(rows=1, cols=1).cell(0, 0).text = "nested FindMe1 here"

        DocumentProcessor(config, mock_logger).transform_text(
            doc, DocxIndexer(doc, mock_logger), config.transform.text_transforms
        )

        assert doc.tables[0].cell(0, 0).tables[0].cell(0, 0).text == "nested Found here"

    def test_merged_cell_is_processed_once(self, tmp_path, mock_logger):
        config = make_config(tmp_path, text=[(r"FindMe\d", "Found")], find_only=True)
        doc = Document()
        table = doc.add_table(rows=1, cols=3)
        table.cell(0, 0).merge(table.cell(0, 2)).text = "merged FindMe1"

        DocumentProcessor(config, mock_logger).transform_text(
            doc, DocxIndexer(doc, mock_logger), config.transform.text_transforms
        )

        assert len(match_logs(mock_logger)) == 1


class TestLogging:
    def test_csv_fields_with_commas_and_quotes_round_trip(self):
        adapter = ContextLoggerAdapter(logging.getLogger("csv-test"), {"document_name": 'a,"b".docx', "match": "True"})
        line, _ = adapter.process('Match: "South32", here', {})
        fields = next(csv.reader([line]))
        assert fields[1] == 'a,"b".docx'
        assert fields[7] == "True"
        assert fields[8] == 'Match: "South32", here'
        assert fields[2] == "unknown"  # missing context field


class TestParallelBatch:
    def test_process_pool_processes_documents_and_reports_failures(self, tmp_path):
        (tmp_path / "in").mkdir()
        shutil.copy(DATA_DIR / "MocWordDoc.docx", tmp_path / "in" / "a.docx")
        shutil.copy(DATA_DIR / "MocWordDoc.docx", tmp_path / "in" / "b.docx")
        (tmp_path / "in" / "broken.docx").write_text("not a docx")
        config = make_config(tmp_path, text=[(r"FindMe\d", "Found")], workers=2)

        batch = BatchProcessor(config, setup_logger(config))
        batch.process_all_docx_parallel()

        assert (batch.processed_count, batch.failed_count) == (2, 1)
        for name in ("a.docx", "b.docx"):
            text = "\n".join(p.text for p in Document(tmp_path / "out" / name).paragraphs)
            assert "Found" in text and "FindMe1" not in text
        # Worker log records reach the parent's CSV log.
        log = (tmp_path / "run.csv").read_text(encoding="utf-8")
        assert "a.docx" in log and "b.docx" in log and "broken.docx" in log

    def test_find_only_does_not_create_output_directories(self, tmp_path):
        (tmp_path / "in" / "sub").mkdir(parents=True)
        shutil.copy(DATA_DIR / "Test-Doc_ver3.docx", tmp_path / "in" / "sub" / "a.docx")
        config = make_config(tmp_path, text=[(r"FindMe\d", "Found")], find_only=True)

        BatchProcessor(config, setup_logger(config)).process_all_docx()

        assert not (tmp_path / "out").exists()
