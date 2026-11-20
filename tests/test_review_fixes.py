"""Tests for the fixes from the code review: coverage, headings, config validation, errors, console."""

import io
import logging
import shutil
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from docx_processor import process_documents
from docx_processor.cli import cli
from docx_processor.config import AppConfig, ConfigError, RegexTransform, RuntimeConfig, TransformConfig, preflight
from docx_processor.logger import ContextLoggerAdapter, CustomFormatter
from docx_processor.processors import BatchProcessor, DocumentProcessor
from docx_processor.processors.docx_indexer import DocxIndexer

DATA_DIR = Path(__file__).parent / "data"
NS_EXTRA = (
    'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
    'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
    'xmlns:v="urn:schemas-microsoft-com:vml"'
)


def make_config(tmp_path, text=(), url=(), find_only=False):
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
            workers=1,
            sync_mode=True,
            find_only=find_only,
            verbose=0,
        ),
    )


@pytest.fixture
def log():
    logger = Mock()
    logger.extra = {}
    return logger


def match_logs(logger):
    return [c.args[0] for c in logger.info.call_args_list if str(c.args[0]).startswith("Match:")]


def run_text(doc, config, logger):
    """Run the text pass the way process_document does: body, then every header/footer."""
    processor, index = DocumentProcessor(config, logger), DocxIndexer(doc, logger)
    processor.transform_text(doc, index, config.transform.text_transforms)
    for label, header_footer in processor._headers_footers(doc):
        processor.transform_text(header_footer, index, config.transform.text_transforms, section=label)


SOUTH32 = [(r"South\s?32", "GM3")]


class TestCoverage:
    def test_header_and_footer_text_is_replaced(self, tmp_path, log):
        doc = Document()
        section = doc.sections[0]
        section.different_first_page_header_footer = True
        section.header.paragraphs[0].text = "South32 header"
        section.footer.paragraphs[0].text = "South32 footer"
        section.first_page_header.paragraphs[0].text = "South32 first page"

        run_text(doc, make_config(tmp_path, SOUTH32), log)

        assert section.header.paragraphs[0].text == "GM3 header"
        assert section.footer.paragraphs[0].text == "GM3 footer"
        assert section.first_page_header.paragraphs[0].text == "GM3 first page"

    def test_text_box_both_copies_replaced_and_logged_once(self, tmp_path, log):
        doc = Document()
        box = "<w:txbxContent><w:p><w:r><w:t>South32 in a box</w:t></w:r></w:p></w:txbxContent>"
        doc.add_paragraph()._p.append(
            parse_xml(
                f"<w:r {nsdecls('w')} {NS_EXTRA}><mc:AlternateContent>"
                f'<mc:Choice Requires="wps"><w:drawing><wps:wsp><wps:txbx>{box}</wps:txbx></wps:wsp></w:drawing>'
                f"</mc:Choice>"
                f"<mc:Fallback><w:pict><v:shape><v:textbox>{box}</v:textbox></v:shape></w:pict></mc:Fallback>"
                f"</mc:AlternateContent></w:r>"
            )
        )

        run_text(doc, make_config(tmp_path, SOUTH32), log)

        texts = [t.text for t in doc.element.body.xpath(".//w:txbxContent//w:t")]
        assert texts == ["GM3 in a box", "GM3 in a box"]
        assert len(match_logs(log)) == 1

    def test_content_controls_block_and_inline(self, tmp_path, log):
        doc = Document()
        doc.element.body.insert(
            0,
            parse_xml(
                f"<w:sdt {nsdecls('w')}><w:sdtContent><w:p><w:r><w:t>South32 block</w:t></w:r></w:p>"
                f"</w:sdtContent></w:sdt>"
            ),
        )
        inline = doc.add_paragraph("Company: ")
        inline._p.append(
            parse_xml(f"<w:sdt {nsdecls('w')}><w:sdtContent><w:r><w:t>South32</w:t></w:r></w:sdtContent></w:sdt>")
        )

        run_text(doc, make_config(tmp_path, SOUTH32), log)

        texts = [t.text for t in doc.element.body.xpath(".//w:sdtContent//w:t")]
        assert texts == ["GM3 block", "GM3"]

    def test_picture_in_run_inside_match_is_kept(self, tmp_path, log):
        doc = Document()
        para = doc.add_paragraph()
        para.add_run("Sou")
        para._p.append(parse_xml(f"<w:r {nsdecls('w')}><w:drawing/></w:r>"))  # picture run, no text
        para.add_run("th32 site")

        run_text(doc, make_config(tmp_path, SOUTH32), log)

        assert para.text == "GM3 site"
        assert len(para._p.xpath(".//w:drawing")) == 1


class TestHeadings:
    def heading_for(self, doc, paragraph):
        return DocxIndexer(doc, Mock()).find_closest_heading_above(paragraph)

    def test_custom_style_based_on_heading_1(self):
        doc = Document()
        chapter = doc.styles.add_style("Chapter", WD_STYLE_TYPE.PARAGRAPH)
        chapter.base_style = doc.styles["Heading 1"]
        doc.add_paragraph("Intro", style="Chapter")
        body = doc.add_paragraph("Body")
        assert self.heading_for(doc, body) == "H1 Intro"

    def test_style_with_own_outline_level(self):
        doc = Document()
        style = doc.styles.add_style("Sub Topic", WD_STYLE_TYPE.PARAGRAPH)
        style.element.get_or_add_pPr().append(parse_xml(f'<w:outlineLvl {nsdecls("w")} w:val="2"/>'))
        doc.add_paragraph("Topic", style="Sub Topic")
        body = doc.add_paragraph("Body")
        assert self.heading_for(doc, body) == "H3 Topic"

    def test_paragraph_outline_level_overrides_style(self):
        doc = Document()
        heading = doc.add_paragraph("Manual heading")
        heading._p.get_or_add_pPr().append(parse_xml(f'<w:outlineLvl {nsdecls("w")} w:val="1"/>'))
        not_heading = doc.add_heading("Demoted", level=1)
        not_heading._p.get_or_add_pPr().append(parse_xml(f'<w:outlineLvl {nsdecls("w")} w:val="9"/>'))
        body = doc.add_paragraph("Body")
        assert self.heading_for(doc, body) == "H2 Manual heading"

    def test_lowercase_heading_name_without_outline_level(self):
        doc = Document()
        doc.styles.add_style("heading 7 custom", WD_STYLE_TYPE.PARAGRAPH)  # not a heading: name doesn't match
        doc.styles.add_style("HEADING 4", WD_STYLE_TYPE.PARAGRAPH)
        doc.add_paragraph("Not a heading", style="heading 7 custom")
        doc.add_paragraph("Upper", style="HEADING 4")
        body = doc.add_paragraph("Body")
        assert self.heading_for(doc, body) == "H4 Upper"


class TestConfigValidation:
    def load(self, tmp_path, text):
        path = tmp_path / "config.yml"
        path.write_text(text, encoding="utf-8")
        return TransformConfig.from_yaml(path)

    def test_empty_file_is_an_empty_config(self, tmp_path):
        config = self.load(tmp_path, "")
        assert config.is_empty and config.drop_matches == []

    @pytest.mark.parametrize(
        "text, message",
        [
            ("text_transforms:\n  - from: 'South(32'\n    to: GM3\n", "text_transforms rule 1"),
            ("url_transforms:\n  - from: 'a'\n    to: '\\1'\n", "invalid group reference"),
            ("text_transforms:\n  - from: '(?P<x>a)'\n    to: '\\g<y>'\n", "unknown group name"),
            ("text_transforms:\n  - from: a\n", "must have string 'from' and 'to'"),
            ("text_transform:\n  - from: a\n    to: b\n", "unknown key(s) text_transform"),
            ("drop_matches: 5\n", "drop_matches must be a list of strings"),
            ("- a\n- b\n", "expected a mapping"),
            ("text_transforms: [\n", "invalid YAML"),
        ],
    )
    def test_invalid_configs_raise_clear_errors(self, tmp_path, text, message):
        with pytest.raises(ConfigError, match=message.replace("(", r"\(").replace(")", r"\)")):
            self.load(tmp_path, text)


class TestPreflight:
    def test_destination_inside_source_is_an_error_in_modify_mode(self, tmp_path):
        (tmp_path / "in").mkdir()
        config = make_config(tmp_path, SOUTH32)
        config.runtime.destination_dir = tmp_path / "in" / "output"
        assert any("inside it" in e for e in preflight(config).errors)

        config.runtime.find_only = True
        assert preflight(config).ok

    def test_batch_ignores_files_in_destination_inside_source(self, tmp_path):
        (tmp_path / "in" / "output").mkdir(parents=True)
        shutil.copy(DATA_DIR / "Test-Doc_ver3.docx", tmp_path / "in" / "a.docx")
        shutil.copy(DATA_DIR / "Test-Doc_ver3.docx", tmp_path / "in" / "output" / "a.docx")
        config = make_config(tmp_path, SOUTH32, find_only=True)
        config.runtime.destination_dir = tmp_path / "in" / "output"

        paths = BatchProcessor(config, Mock())._get_document_paths()

        assert [p.relative_to(tmp_path / "in").as_posix() for p in paths] == ["a.docx"]


class TestCli:
    def invoke(self, tmp_path, config_text, *args, dest="out"):
        (tmp_path / "in").mkdir(exist_ok=True)
        shutil.copy(DATA_DIR / "Test-Doc_ver3.docx", tmp_path / "in" / "a.docx")
        (tmp_path / "config.yml").write_text(config_text, encoding="utf-8")
        base = ["-c", str(tmp_path / "config.yml"), "--source-dir", str(tmp_path / "in")]
        base += ["--dest-dir", str(tmp_path / dest), "--log-file", str(tmp_path / "run.log")]
        return CliRunner().invoke(cli, base + list(args), obj={})

    def test_validate_rejects_invalid_regex(self, tmp_path):
        result = self.invoke(tmp_path, "text_transforms:\n  - from: 'South(32'\n    to: GM3\n", "validate")
        assert result.exit_code != 0
        assert "text_transforms rule 1" in result.output
        assert "valid! ✓" not in result.output

    def test_validate_and_run_refuse_overlapping_folders_in_modify_mode(self, tmp_path):
        config = "text_transforms:\n  - from: 'South32'\n    to: GM3\n"
        result = self.invoke(tmp_path, config, "--modify", "validate", dest="in/output")
        assert result.exit_code == 2 and "inside it" in result.output

        result = self.invoke(tmp_path, config, "--modify", "--sync", "run", dest="in/output")
        assert result.exit_code == 2
        assert not (tmp_path / "in" / "output").exists()

    def test_validate_passes_for_good_config(self, tmp_path):
        result = self.invoke(tmp_path, "text_transforms:\n  - from: 'South32'\n    to: GM3\n", "validate")
        assert result.exit_code == 0, result.output
        assert "1 .docx file(s) found" in result.output and "valid! ✓" in result.output


class TestErrorsAndConsole:
    def test_error_message_is_not_truncated(self, tmp_path, log):
        missing = tmp_path / "missing.docx"
        assert (
            DocumentProcessor(make_config(tmp_path, SOUTH32), log).process_document(missing, tmp_path / "o.docx")
            is False
        )
        message = log.error.call_args.args[0]
        assert str(missing) in message and "PackageNotFoundError" in message

    def test_console_line_is_readable_not_csv(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(CustomFormatter())
        base = logging.getLogger("console-test")
        base.handlers[:] = [handler]
        base.setLevel(logging.INFO)
        base.propagate = False
        context = {"document_name": "a.docx", "document_full_path": "C:\\docs", "section": "Body"}
        adapter = ContextLoggerAdapter(base, {**context, "location": "H1 Intro", "table_row": "", "match": "True"})

        adapter.info("Match: 1 match for 'South32'")

        line = stream.getvalue().strip()
        assert "a.docx [Body / H1 Intro] Match: 1 match for 'South32'" in line
        assert "C:\\docs" not in line  # CSV-only columns stay out of the console line

    def test_process_documents_is_a_library_entry_point(self, tmp_path):
        (tmp_path / "in").mkdir()
        shutil.copy(DATA_DIR / "Test-Doc_ver3.docx", tmp_path / "in" / "a.docx")
        assert process_documents(make_config(tmp_path, SOUTH32)) == 0
        assert (tmp_path / "out" / "a.docx").exists()
