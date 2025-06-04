"""
Command-line interface for docx-processor.
"""
import asyncio
import sys
from pathlib import Path

from config import TransformConfig

import click

from config import AppConfig, RuntimeConfig
from docx_processor.config.app_config import RegexTransform
from processors import BatchProcessor

from logging import Logger
from logger import setup_logger


def process_documents(config: AppConfig) -> int:
  """Process documents based on configuration."""
  try:
    logger: Logger = setup_logger(config)
  except Exception as e:
    print(f"Failed to initialize logger: {e}")  # Fallback error reporting
    return 1

  try:
    processor = BatchProcessor(
      config=config,
      logger=logger,
  #    max_workers=config.runtime.workers,
  #    find_only=config.runtime.find_only
    )

    if config.runtime.sync_mode:
      processor.process_all_docx()
    else:

      asyncio.run(processor.process_all_docx_async())

    logger.info("Processing completed successfully")
    return 0

  except Exception as e:
    logger.error(f"Processing failed: {e}")
    return 1

@click.group()
@click.option(
  '-c', '--config',
  type=click.Path(exists=True, path_type=Path),
  required=True,
  help='Path to transforms configuration file (YAML)'
)
@click.option(
  '--source-dir',
  type=click.Path(exists=True, path_type=Path),
  required=True,
  help='Source directory containing documents to process'
)
@click.option(
  '--dest-dir',
  type=click.Path(path_type=Path),
  required=True,
  help='Destination directory for processed documents'
)
@click.option(
  '--log-file',
  type=click.Path(path_type=Path),
  required=True,
  help='Path to log file'
)
@click.option(
  '--log-level',
  type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'], case_sensitive=False),
  default='WARNING',
  help='Logging level'
)
@click.option(
  '--workers',
  type=click.IntRange(min=1),
  default=4,
  help='Number of worker threads for async processing',
  show_default=True
)
@click.option(
  '--sync/--async',
  'sync_mode',
  default=False,
  help='Use synchronous processing instead of async'
)
@click.option(
  '--find-only/--modify',
  default=True,
  help='Only find and log matches without modifying them',
  show_default=True
)
@click.option(
  '--verbose', '-v',
  count=True,
  help='Increase verbosity (can be used multiple times)'
)
@click.pass_context
def cli(ctx: click.Context, config: Path, source_dir: Path, dest_dir: Path,
        log_file: Path, log_level: str, workers: int, sync_mode: bool,
        find_only: bool, verbose: int):
  """DocX Processor - Process Word documents with configured transformations."""
  ctx.ensure_object(dict)

  try:
    # Load transform config from YAML
    transform_config = TransformConfig.from_yaml(config)

    # Create runtime config from CLI options
    runtime_config = RuntimeConfig(
      source_dir=source_dir,
      destination_dir=dest_dir,
      log_file=log_file,
      log_level=log_level,
      workers=workers,
      sync_mode=sync_mode,
      find_only=find_only,
      verbose=verbose
    )

    # Create combined config
    app_config = AppConfig(
      transform=transform_config,
      runtime=runtime_config
    )

    ctx.obj['config'] = app_config

  except Exception as e:
    raise click.ClickException(str(e))

@cli.command()
@click.pass_context
def run(ctx: click.Context):
    """Process documents according to configuration."""
    config = ctx.obj['config']
    process_documents(config)

@cli.command()
@click.pass_context
def validate(ctx: click.Context):
  from config.constants import DEFAULT_LOG_LEVEL

  """Validate configuration without processing documents.

  This command performs a dry-run validation of the configuration,
  checking that all paths exist and patterns are valid.
  """
  config = ctx.obj['config']
  click.echo("Configuration validation:")
  click.echo(f"  Source directory: {config.runtime.source_dir}")
  click.echo(f"  Destination directory: {config.runtime.destination_dir}")
  click.echo(f"  Log file: {config.runtime.log_file}")
  click.echo(f"  Log level (Default): {config.runtime.log_level} (default: {DEFAULT_LOG_LEVEL})")
  if config.runtime.verbose:
    click.echo(f"  Log level (run): {config.runtime.verbose}")
  click.echo(f"  Processing mode: {'sync' if config.runtime.sync_mode else 'async'}")
  click.echo(f"  Workers: {config.runtime.workers}")
  click.echo(f"  Operation: {'find-only' if config.runtime.find_only else 'modify'}")
  click.echo("\nURL patterns:")
  for transform in config.transform.url_transforms:
    click.echo(f"from: {transform.from_pattern} → to: {transform.to_pattern}")
  click.echo("\nConfiguration is valid! ✓")

@cli.command()
@click.pass_context
def info(ctx: click.Context):
  """Display information about current configuration.

  Shows detailed information about the current configuration,
  including paths, patterns, and runtime settings.
  """
  config = ctx.obj['config']
  click.echo(click.style("Runtime Configuration", fg='green', bold=True))
  click.echo(f"Workers: {config.run_config.workers}")
  click.echo(f"Mode: {'Synchronous' if config.run_config.sync_mode else 'Asynchronous'}")
  click.echo(f"Operation: {'Find Only' if config.run_config.find_only else 'Modify'}")
  click.echo(f"Verbosity: {config.run_config.verbose}")

  click.echo("\n" + click.style("Paths", fg='green', bold=True))
  click.echo(f"Source: {config.source_dir}")
  click.echo(f"Destination: {config.destination_dir}")
  click.echo(f"Log File: {config.log_file}")

  click.echo("\n" + click.style("URL Patterns", fg='green', bold=True))
  for pattern in config.url_config.find_patterns:
    click.echo(f"Find: {pattern}")
  for find, replace in config.url_config.replace_patterns.items():
    click.echo(f"Replace: {find} → {replace}")


def main():
  """Entry point for the CLI application."""
  cli(obj={})


if __name__ == "__main__":
  main()