"""
docx_processor - A tool for processing and modifying Word DOCX files.

Copyright (c) 2024 Sean Smith
Licensed under the MIT License. See LICENSE file for details.
"""

from .config import AppConfig, ConfigError, RuntimeConfig, TransformConfig
from .logger import DocxLogger, ContextLoggerAdapter
from .processors import DocxIndexer
from .processors.batch import BatchProcessor
from .processors.document import DocumentProcessor
from .version import __version__
from .cli import process_documents  # noqa: E402 - library entry point (imports the modules above)

__author__ = "Sean Smith"
__copyright__ = "Copyright (c) 2024 Sean Smith"
__license__ = "MIT"

__all__ = [
    "process_documents",
    "DocumentProcessor",
    "BatchProcessor",
    "AppConfig",
    "TransformConfig",
    "RuntimeConfig",
    "ConfigError",
    "DocxLogger",
    "ContextLoggerAdapter",
    "DocxIndexer",
    "__version__",
]
