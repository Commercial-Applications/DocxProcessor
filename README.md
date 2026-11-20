# DocxProcessor

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/Commercial-Applications/DocxProcessor)](https://github.com/Commercial-Applications/DocxProcessor/releases)
[![License](https://img.shields.io/github/license/Commercial-Applications/DocxProcessor)](https://github.com/Commercial-Applications/DocxProcessor/blob/master/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://github.com/Commercial-Applications/DocxProcessor/actions/workflows/python-package.yml/badge.svg?branch=master)](https://github.com/Commercial-Applications/DocxProcessor/actions/workflows/python-package.yml)
[![Security Check](https://github.com/Commercial-Applications/DocxProcessor/actions/workflows/security.yml/badge.svg?branch=master)](https://github.com/Commercial-Applications/DocxProcessor/actions/workflows/security.yml)


## Requires

* Python 3.11 or later
* python-docx 1.2.0 or later

## Description

Will modify Embedded URL's that match HTTPS? pattern and replace with [regex]
urls that do not match pattern are not changed.

Text that matches a `text_transforms` pattern is replaced in `--modify` mode (and only logged in `--find-only` mode).
Paragraphs containing any `drop_matches` phrase are skipped.

Works with the document xml so does not require word to be opened for each file.

## Functional within:

URL and text rules apply in all of these places:

* Body text
* Headers and footers of every section (including first-page and even-page variants)
* Tables, including nested tables
* Text boxes and content controls
* Hyperlink targets and their visible text

Also:

* URL matching is case insensitive; both http and https are captured
* URL rules are applied in order, each to the result of the previous one
* Will identify and rename styles
* Will identify multiple text patterns within a paragraph. NOTE: A matched paragraph may contain 1 or more instances of
  pattern.
* Log locations show the nearest heading, including custom heading styles (detected by outline level)

## Note:

There are some edge cases that may cause issues.
Works only on current word .docx (xml) not .doc

## License

Copyright (c) 2025 Cravern
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Installation

pip install git+https://github.com/Commercial-Applications/DocxProcessor.git


## Options

| Option                 | Type    | Description                                                | Default       |
|------------------------|---------|------------------------------------------------------------|---------------|
| `-c, --config PATH`    | Path    | Path to YAML configuration file containing transform rules | *Required*    |
| `--source-dir PATH`    | Path    | Directory containing Word documents to process             | *Required*    |
| `--dest-dir PATH`      | Path    | Output directory for processed documents                   | *Required*    |
| `--log-file PATH`      | Path    | Log file path (written as CSV; extension becomes `.csv`)   | *Required*    |
| `--log-level`          | Choice  | Logging level (`DEBUG`\|`INFO`\|`WARNING`\|`ERROR`)        | `WARNING`     |
| `--workers`            | Integer | Number of worker processes for `--async` mode (min: 1)     | `4`           |
| `--sync/--async`       | Flag    | `--sync`: one document at a time; `--async`: in parallel   | `--async`     |
| `--find-only/--modify` | Flag    | Only find and log matches without modifying documents      | `--find-only` |
| `-v, --verbose`        | Count   | Increase output verbosity (can be used multiple times)     | `0`           |
| `--help`               | Flag    | Show help message and exit                                 |               |

## Examples

Options go **before** the command (`validate` or `run`). Keep the destination folder **outside** the source folder:
in `--modify` mode the tool refuses to run otherwise.

A typical layout:

```
rebrand/
├── transforms.yml   # your rules (see Sample Config)
├── docs_in/         # original documents (never modified)
└── docs_out/        # changed copies are written here in --modify mode
```

### Install

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install git+https://github.com/Commercial-Applications/DocxProcessor.git
```

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install git+https://github.com/Commercial-Applications/DocxProcessor.git
```

### 1. Check the configuration first

Linux / macOS:

```bash
docx-processor -c transforms.yml \
  --source-dir ./docs_in \
  --dest-dir ./docs_out \
  --log-file ./process.log \
  --modify \
  validate
```

Windows (PowerShell; the backtick continues a line):

```powershell
docx-processor -c transforms.yml `
  --source-dir .\docs_in `
  --dest-dir .\docs_out `
  --log-file .\process.log `
  --modify `
  validate
```

Include `--modify` here if you plan to modify, so the destination-folder checks run too.

### 2. Preview the matches (default: nothing is changed)

Writes every match to `process.csv`. The console shows the same matches at `--log-level INFO`.

Linux / macOS:

```bash
docx-processor -c transforms.yml \
  --source-dir ./docs_in \
  --dest-dir ./docs_out \
  --log-file ./process.log \
  --log-level INFO \
  run
```

Windows (PowerShell):

```powershell
docx-processor -c transforms.yml `
  --source-dir .\docs_in `
  --dest-dir .\docs_out `
  --log-file .\process.log `
  --log-level INFO `
  run
```

### 3. Apply the changes

Writes changed copies to `docs_out`, processing 8 documents at a time:

Linux / macOS:

```bash
docx-processor -c transforms.yml \
  --source-dir ./docs_in \
  --dest-dir ./docs_out \
  --log-file ./process.log \
  --modify \
  --workers 8 \
  run
```

Windows (PowerShell):

```powershell
docx-processor -c transforms.yml `
  --source-dir .\docs_in `
  --dest-dir .\docs_out `
  --log-file .\process.log `
  --modify `
  --workers 8 `
  run
```

Windows (Command Prompt; `^` continues a line):

```bat
docx-processor -c transforms.yml ^
  --source-dir docs_in ^
  --dest-dir docs_out ^
  --log-file process.log ^
  --modify ^
  --workers 8 ^
  run
```

### 4. Troubleshoot one document at a time with full detail

`--sync` processes documents one by one; `DEBUG` adds per-paragraph detail and full error tracebacks.

Linux / macOS:

```bash
docx-processor -c transforms.yml --source-dir ./docs_in --dest-dir ./docs_out \
  --log-file ./debug.log --sync --log-level DEBUG run
```

Windows (PowerShell):

```powershell
docx-processor -c transforms.yml --source-dir .\docs_in --dest-dir .\docs_out `
  --log-file .\debug.log --sync --log-level DEBUG run
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Success |
| `1`  | One or more documents failed (see the log) |
| `2`  | Configuration or folder problem found before processing; nothing was processed |

Check it with `echo $?` (Linux / macOS) or `$LASTEXITCODE` (PowerShell).

The repository also has ready-made wrapper scripts that preview matches (find-only) with `--workers 10 -v`:

- `run_docxp.ps1` (Windows): uses `config.yml`, `docs_in` and `docs_out` next to the script
- `run_docxp.sh` (Linux / macOS): uses `config.yaml`, `docs_in` and `docs_out` in the current folder

### Validate

Validates configuration without processing documents and exits non-zero if anything is wrong. It checks:

- Configuration file syntax and structure (unknown keys, rules missing `from`/`to`)
- Every regular expression and replacement compiles (e.g. unbalanced brackets, bad `\1` group references)
- Source directory is readable and contains `.docx` files
- In `--modify` mode: destination is writable and is **not** inside the source directory
  (outputs would otherwise be processed again on the next run)

`run` performs the same checks first and processes nothing if any fail.

Output includes:

- Directory paths
- Processing mode configuration
- Worker settings
- Operation mode
- URL patterns and replacements

## Use as a library

```python
from pathlib import Path
from docx_processor import AppConfig, RuntimeConfig, TransformConfig, process_documents

config = AppConfig(
    transform=TransformConfig.from_yaml(Path("transforms.yaml")),
    runtime=RuntimeConfig(source_dir=Path("docs"), destination_dir=Path("output"), log_file=Path("process.log"),
                          log_level="WARNING", workers=4, sync_mode=False, find_only=True, verbose=0),
)
exit_code = process_documents(config)  # 0 = success, 1 = a document failed, 2 = configuration problem
```

## Sample Config

```yaml
url_transforms:
  - from: "(www\\.)?south32\\.net"
    to: "gm3.au" # www not required
  - from: ".*/s[sS]outh32/s.*"
    to: "GM3"
text_transforms:
  - from: "South\\s?32"
    to: "GM3"
  - from: "\\bS32\\b" # use \b (word boundary), \s would also replace the surrounding spaces
    to: "GM3"
style_transforms:
  - from: "Glencore"
    to: "GM3"
drop_matches: # paragraphs containing any of these phrases are skipped (e.g. document change logs)
  - "Updated South32 to GM3 branding"
```

## Notes

- The `--config` file should be a YAML file containing transform rules for URLs, text, and styles
- Use `--find-only` first to verify matches before applying modifications
- Verbose mode (`-v`) can be used multiple times (`-vv`, `-vvv`) for increased detail
- Worker count should be adjusted based on available CPU cores

