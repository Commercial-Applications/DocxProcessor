"""
Command-line interface for docx-processor.
"""

import asyncio
from logging import Logger
from pathlib import Path

import click

from .config import AppConfig, RuntimeConfig, TransformConfig
from .logger import setup_logger
from .processors import BatchProcessor
from .version import __version__


def process_documents(config: AppConfig) -> int:
    """Process documents based on configuration."""
    try:
        logger: Logger = setup_logger(config)
    except Exception as e:
        print(f"Failed to initialize logger: {e}")  # Fallback error reporting
        return 1

    try:
        processor = BatchProcessor(config=config, logger=logger)

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
@click.version_option(version=__version__, prog_name="docx-processor")
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to transforms configuration file (YAML)",
)
@click.option(
    "--source-dir",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Source directory containing documents to process",
)
@click.option(
    "--dest-dir", type=click.Path(path_type=Path), required=True, help="Destination directory for processed documents"
)
@click.option("--log-file", type=click.Path(path_type=Path), required=True, help="Path to log file")
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="WARNING",
    help="Logging level",
)
@click.option(
    "--workers",
    type=click.IntRange(min=1),
    default=4,
    help="Number of worker threads for async processing",
    show_default=True,
)
@click.option("--sync/--async", "sync_mode", default=False, help="Use synchronous processing instead of async")
@click.option(
    "--find-only/--modify", default=True, help="Only find and log matches without modifying them", show_default=True
)
@click.option("--verbose", "-v", count=True, help="Increase verbosity (can be used multiple times)")
@click.pass_context
def cli(
    ctx: click.Context,
    config: Path,
    source_dir: Path,
    dest_dir: Path,
    log_file: Path,
    log_level: str,
    workers: int,
    sync_mode: bool,
    find_only: bool,
    verbose: int,
):
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
            verbose=verbose,
        )

        # Create combined config
        app_config = AppConfig(transform=transform_config, runtime=runtime_config)

        ctx.obj["config"] = app_config

    except Exception as e:
        raise click.ClickException(str(e))


@cli.command()
@click.pass_context
def run(ctx: click.Context):
    """Process documents according to configuration."""
    config = ctx.obj["config"]
    process_documents(config)


@cli.command()
@click.pass_context
def validate(ctx: click.Context):
    from config.constants import DEFAULT_LOG_LEVEL

    """Validate configuration without processing documents.
    This command performs a dry-run validation of the configuration,
    checking that all paths exist and patterns are valid.
    """
    config = ctx.obj["config"]
    click.echo("Configuration validation:")
    click.echo(f"  Version: {__version__}")
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
    for url in config.transform.url_transforms:
        click.echo(f"from: {url.from_pattern} → to: {url.to_pattern}")
    click.echo("\nStyle patterns:")
    for style in config.transform.style_transforms:
        click.echo(f"from: {style.from_pattern} → to: {style.to_pattern}")
    click.echo("\nText patterns:")
    for text in config.transform.text_transforms:
        click.echo(f"from: {text.from_pattern} → to: {text.to_pattern}")

    click.echo("\nConfiguration is valid! ✓")


def main():
    """Entry point for the CLI application."""
    cli(obj={})


if __name__ == "__main__":
    main()
