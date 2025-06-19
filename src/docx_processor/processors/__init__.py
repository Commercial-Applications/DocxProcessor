"""
Core processing components for DOCX files.
"""

from .batch import BatchProcessor
from .document import DocumentProcessor
from .docx_indexer import DocxIndexer

__all__ = ["DocumentProcessor", "BatchProcessor", "DocxIndexer"]
