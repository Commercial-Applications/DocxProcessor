"""
docx_processor - A tool for processing and modifying Word DOCX files.

Copyright (c) 2024 Sean Smith
Licensed under the MIT License. See LICENSE file for details.
"""


from .processors.document import DocumentProcessor
from .processors.batch import BatchProcessor
from .config import Config
from .logger import DocxLogger, ContextLoggerAdapter

__version__ = "0.1.0"
__author__ = "Sean Smith"
__copyright__ = "Copyright (c) 2024 Sean Smith"
__license__ = "MIT"

__all__ = [
    'DocumentProcessor',
    'BatchProcessor',
    'Config',
    'DocxLogger',
    'ContextLoggerAdapter',
]
