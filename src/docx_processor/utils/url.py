import zipfile
from pathlib import Path

from lxml import etree


def non_rel_hyperlinks(logger, file_path: Path) -> None:  # noqa: C901

    logger.extra.update({"module": "non_rel_hyperlinks", "task": "non_rel_hyperlinks"})

    with zipfile.ZipFile(file_path) as docx:
        try:
            with zipfile.ZipFile(file_path) as docx:
                try:
                    xml_content = docx.read("word/document.xml")
                    tree = etree.fromstring(xml_content)
                    return tree, {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                except zipfile.BadZipFile:
                    logger.error("Corrupt ZIP structure in document")
                    return None
                except KeyError:
                    logger.error("Missing word/document.xml")
                    return None
                except etree.XMLSyntaxError:
                    logger.error("Invalid XML content")
                    return None

        except zipfile.BadZipFile as e:
            logger.error(f"Unable to open document {file_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error processing {file_path}: {str(e)}")
            return None

    # Namespaces
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    # Find all field code runs
    instr_texts = tree.xpath("//w:instrText", namespaces=ns)

    for instr in instr_texts:
        if instr.text and "HYPERLINK" in instr.text:
            # Extract the URL inside the HYPERLINK field code
            parts = instr.text.split('"')
            if len(parts) >= 2:
                logger.extra["match"] = "True"
                logger.extra["section"] = "XML"
                logger.info(f"Non-Rel URL: {parts[1]} (Non-standard URL embedding)")
                logger.extra["match"] = "False"
