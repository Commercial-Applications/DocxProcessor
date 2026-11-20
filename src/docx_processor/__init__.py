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


def __getattr__(name):
    # process_documents lives in .cli. Importing it lazily keeps `python -m docx_processor.cli`
    # from loading cli twice (once via this package, once as __main__), which triggers a
    # runpy RuntimeWarning.
    if name == "process_documents":
        from .cli import process_documents

        return process_documents
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
