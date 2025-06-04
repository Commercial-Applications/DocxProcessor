# src/docx_processor/processors/batch.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .document import DocumentProcessor
from pathlib import Path


class BatchProcessor:
  def __init__(self, config, logger):
    self.config = config
    self.logger = logger
    self.workers = config.runtime.workers
    self.find_only = config.runtime.find_only

  def process_all_docx(self) -> None:
    """Process all documents in the source directory synchronously."""
    for input_path in self._get_document_paths():
      processor = DocumentProcessor(self.config, self.logger)
      relative_path = input_path.relative_to(self.config.runtime.source_dir)
      output_path = self._get_output_path(relative_path)
      processor.process_document(input_path, output_path)

  async def process_all_docx_async(self) -> None:
    """Process all documents in the source directory asynchronously."""
    paths = list(self._get_document_paths())

    # Create a thread pool for CPU-bound document processing
    with ThreadPoolExecutor(max_workers=self.workers) as executor:
      loop = asyncio.get_event_loop()
      tasks = []

      for input_path in paths:
        relative_path = input_path.relative_to(self.config.runtime.source_dir)
        output_path = self._get_output_path(relative_path)

        # Create task for each document
        task = loop.run_in_executor(
          executor,
          self._process_single_document,
          input_path,
          output_path
        )
        tasks.append(task)

      # Wait for all tasks to complete
      await asyncio.gather(*tasks)

  def _process_single_document(self, input_path: Path, output_path: Path) -> None:
    """Helper method to process a single document."""
    processor = DocumentProcessor(self.config, self.logger)
    processor.process_document(input_path, output_path)

  def _get_document_paths(self):
    """Get all valid document paths."""
    for input_path in self.config.runtime.source_dir.rglob("*.docx"):
      if not input_path.name.startswith("~$"):  # Skip temporary Word files
        yield input_path

  def _get_output_path(self, relative_path: Path) -> Path:
    """Get output path and ensure directory exists."""
    output_path = self.config.runtime.destination_dir / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path
