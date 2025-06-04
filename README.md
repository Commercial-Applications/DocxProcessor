
## Requires
* python-dox

## Description
Will modify Embedded URL's that match HTTPS? pattern and replace with [regex]
urls that do not match pattern are not changed.

Works with the document xml so does not require word to be opened for each file.

## Functional within:
* Body text
* Multiple sections of Header and Footer
* Is Case insensitive
* Both http and https are captured

## Pending:
* Tables (This is possible)

## Note:
There are some edge cases that may cause issues.
Works only on current word .docx (xml) not .doc

## License
Copyright (c) 2024 Sean Smith
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## Installation
pip install git+[https://github.com/YOUR-USERNAME/docx-processor.git](https://github.com/Commercial-Applications/docx-processor.git)

## Usage


## Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `-c, --config PATH` | Path | Path to YAML configuration file containing transform rules | *Required* |
| `--source-dir PATH` | Path | Directory containing Word documents to process | *Required* |
| `--dest-dir PATH` | Path | Output directory for processed documents | *Required* |
| `--log-file PATH` | Path | Path where log file will be created | *Required* |
| `--log-level` | Choice | Logging level (`DEBUG`\|`INFO`\|`WARNING`\|`ERROR`) | `INFO` |
| `--workers` | Integer | Number of worker threads for parallel processing (min: 1) | `4` |
| `--sync/--async` | Flag | Run in synchronous mode instead of async | `--async` |
| `--find-only/--modify` | Flag | Only find and log matches without modifying documents | `--find-only` |
| `-v, --verbose` | Count | Increase output verbosity (can be used multiple times) | `0` |
| `--help` | Flag | Show help message and exit | |

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

## Notes
- The `--config` file should be a YAML file containing transform rules for URLs, text, and styles
- Use `--find-only` first to verify matches before applying modifications
- Verbose mode (`-v`) can be used multiple times (`-vv`, `-vvv`) for increased detail
- Worker count should be adjusted based on available CPU cores

