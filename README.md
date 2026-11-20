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

* Body text
* Multiple sections of Header and Footer
* Is Case insensitive
* Both http and https are captured

* Will identify and Name chnage styles
* Will identify multiple text patterns within a paragraph. NOTE: A matched paragraph may contain 1 or more instances of
  pattern.

## Pending:

* Tables (This is possible)

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

### Find matches without modifying (default mode)

bash docx-processor -c transforms.yaml\
--source-dir ./docs\
--dest-dir ./output\
--log-file ./process.log\
run

### Run synchronously with debug logging

bash docx-processor -c transforms.yaml\
--source-dir ./docs\
--dest-dir ./output\
--log-file ./process.log\
--sync\
--log-level DEBUG\
run

### Validate

bash docx-processor -c transforms.yaml\
--source-dir ./docs\
--dest-dir ./output\
--log-file ./process.log\
validate

Validates configuration without processing documents. Performs a dry-run validation checking:

- Configuration file syntax
- Source directory existence
- Destination directory validity
- Pattern validity
- Transform rules

Output includes:

- Directory paths
- Processing mode configuration
- Worker settings
- Operation mode
- URL patterns and replacements

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

