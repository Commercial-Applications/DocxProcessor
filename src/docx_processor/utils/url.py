import zipfile
from lxml import etree
from pathlib import Path

def non_rel_hyperlinks(logger, file_path: Path) -> None:
  # Logs as an Error
  logger.extra.update({
    'module': 'non_rel_hyperlinks',
    'task': 'non_rel_hyperlinks'
  })

  with zipfile.ZipFile(file_path) as docx:
    xml_content = docx.read('word/document.xml')
  tree = etree.fromstring(xml_content)
  # Namespaces
  ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

  # Find all field code runs
  instr_texts = tree.xpath('//w:instrText', namespaces=ns)

  for instr in instr_texts:
    if instr.text and 'HYPERLINK' in instr.text:
      # Extract the URL inside the HYPERLINK field code
      parts = instr.text.split('"')
      if len(parts) >= 2:
        logger.extra['match'] = 'True'
        logger.extra['section'] = 'XML'
        logger.info(f"Non-Rel URL: {parts[1]} (Non-standard URL embedding)")
        logger.extra['match'] = 'False'