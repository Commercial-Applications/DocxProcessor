"""
Command-line interface for docx-processor.
"""
import asyncio
import argparse
import logging
import sys

from config import Config
from logger import ContextLoggerAdapter, DocxLogger
from processors import BatchProcessor

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Process DOCX files to modify URLs and other content."
    )
    parser.add_argument(
        "-c", "--config",
        default="word_docx_morph.ini",
        help="Path to configuration file (default: word_docx_morph.ini)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of worker threads for async processing (default: 4)"
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Use synchronous processing instead of async"
    )
    return parser.parse_args()


async def main():
    """Main entry point for the application."""
    args = parse_args()

    try:
        # Load configuration
        config = Config.from_file(args.config)
        config.validate()

        # Initialize logger
        logger = ContextLoggerAdapter(
            DocxLogger(config.log_file, logging.DEBUG).logger,
            {}
        )

        # Create batch processor
        processor = BatchProcessor(config, logger, max_workers=args.workers)

        # Process files
        if args.sync:
            processor.process_all_docx()
        else:
            await processor.process_all_docx_async()

        logger.info("Processing completed successfully")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cli():
    """Entry point for command-line interface."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli()

