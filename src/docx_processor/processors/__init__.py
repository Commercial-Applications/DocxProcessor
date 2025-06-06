"""
Core processing components for DOCX files.
"""

from .document import DocumentProcessor
from .batch import BatchProcessor
from .docx_indexer import DocxIndexer

__all__ = ['DocumentProcessor', 'BatchProcessor', 'DocxIndexer']
