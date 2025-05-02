# Proof of concept

import logging
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
import re
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(r"C:\Users\SeanSmith\Downloads\log\url_modification.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Utility to process headers
def process_section(name, element, modify_func, url_pattern):
    logging.info(f"Processing section: {name}")

    for para_idx, para in enumerate(element.paragraphs):
        for hyperlink_idx, hyperlink in enumerate(para.hyperlinks):
            for run_idx, run in enumerate(hyperlink.runs):
                if run.text and url_pattern.search(run.text):
                    original: str = run.text
                    new_url: str = modify_func(original)
                    logging.info(f"{name} Link-Text {para_idx}, Run {run_idx}: {original} → {new_url}")
                    run.clear()
                    run.add_text(new_url)

# Need to handle URLs separatley to text
    for rel in element.part.rels.values():
        if rel.reltype == RT.HYPERLINK:
            if url_pattern.search(rel.target_ref):
                original = rel.target_ref
                new_target = modify_func(original)
                logging.info(f"{name} URL: {original} → {new_target}")
                rel._target = new_target

# Modify URL and Save
def modify_urls_in_docx(file_path, output_path, modify_func):
    logging.info(f"Starting URL modification for: {file_path}")
    doc = Document(file_path)
    url_pattern = re.compile(r'https?://[^\s)]+', re.IGNORECASE)

    # Body text
    process_section("Body", doc, modify_func, url_pattern)

    # Headers and footers across all sections
    for idx, section in enumerate(doc.sections):
        process_section(f"Header {idx}", section.header, modify_func, url_pattern)
        process_section(f"Footer {idx}", section.footer, modify_func, url_pattern)

    # Save modified document
    doc.save(output_path)
    logging.info(f"Document saved: {output_path}")

# Run
def process_all_docx(input_dir, output_dir):
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if not file.lower().endswith(".docx"): # Only process Docx
                continue
            if file.startswith("~$"):  # Skip temporary Word files
                continue
            input_path = os.path.join(root, file)

            # Compute relative-path and map to output directory
            relative_path = os.path.relpath(input_path, input_dir)
            output_path = os.path.join(output_dir, relative_path)

            # Ensure destination directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Process file - Corrup Files logged as error
            try:
                modify_urls_in_docx(input_path, output_path, url_replace_regex)
            except Exception as e:
                logging.error(f"Failed to process {input_path}: {e}")

# Regex Replace function
# input: original URL
# outpup: converted url
def url_replace_regex(original_url):
    replace_rgx = r'((?:www.)?south32.net)'
    with_rgx = r'gm3.au'
    return re.sub(replace_rgx, with_rgx, original_url, flags=re.IGNORECASE)

process_all_docx(r"C:\Users\SeanSmith\Downloads\pre", r"C:\Users\SeanSmith\Downloads\post")
