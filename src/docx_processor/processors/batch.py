# src/docx_processor/processors/batch.py
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from docx_processor.logger import ContextLoggerAdapter
from .document import DocumentProcessor


class BatchProcessor:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.workers = config.runtime.workers
        self.find_only = config.runtime.find_only
        self.processed_count = 0
        self.start_time = None

    def process_all_docx(self) -> None:
        """Process all documents in the source directory synchronously."""
        self.start_time = time.time()
        self.processed_count = 0

        for input_path in self._get_document_paths():
            processor = DocumentProcessor(self.config, self.logger)
            relative_path = input_path.relative_to(self.config.runtime.source_dir)
            output_path = self._get_output_path(relative_path)
            processor.process_document(input_path, output_path)
            self.processed_count += 1

        total_time = time.time() - self.start_time
        self.logger.info(f"Processing complete. Documents processed: {self.processed_count}")
        self.logger.info(f"Total processing time: {total_time:.2f} seconds")

    async def process_all_docx_async(self) -> None:
        """Process all documents in the source directory asynchronously."""
        self.start_time = time.time()
        self.processed_count = 0

        paths = list(self._get_document_paths())
        # Create semaphore to limit concurrent tasks
        semaphore = asyncio.Semaphore(self.workers)

        async def process_with_semaphore(input_path, output_path):
            async with semaphore:
                return await self._process_single_document_async(input_path, output_path)

        tasks = []
        for input_path in paths:
            relative_path = input_path.relative_to(self.config.runtime.source_dir)
            output_path = self._get_output_path(relative_path)
            task = process_with_semaphore(input_path, output_path)
            tasks.append(task)

        # Process all tasks concurrently
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        self.processed_count = sum(1 for result in completed if result is True)

        total_time = time.time() - self.start_time
        self.logger.info(f"Processing complete. Documents processed: {self.processed_count}")
        self.logger.info(f"Total processing time: {total_time:.2f} seconds")
        self.logger.info(f"Average time per document: {total_time / max(1, self.processed_count):.2f} seconds")

    async def _process_single_document_async(self, input_path: Path, output_path: Path) -> bool:
        """Process a single document asynchronously."""
        # Create task-specific logger with isolated context so that Async does not hose up logs
        task_logger = ContextLoggerAdapter(
            self.logger.logger,  # Get underlying logger
            {
                'document_name': input_path.name,
                'document_full_path': str(input_path),
                'section': '',
                'module': '',
                'location': 'No Heading',
                'match': 'False'
            }
        )
        try:
            # Run CPU-intensive document processing in a thread pool
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(
                    pool,
                    self._process_single_document,
                    input_path,
                    output_path,
                    task_logger
                )
            return result
        except Exception as e:
            task_logger.logger.error(f"Failed to process {input_path}: {e}")
            return False

    def _process_single_document(self, input_path: Path, output_path: Path, task_logger) -> bool:
        try:
            # Create a new processor instance for each document to avoid state sharing
            processor = DocumentProcessor(self.config, task_logger)
            processor.process_document(input_path, output_path)
            return True
        except Exception as e:
            self.logger.error(f"Failed to process {input_path}: {e}")
            return False

    def _get_document_paths(self):
        """Get all valid document paths."""
        return [
            input_path
            for input_path in self.config.runtime.source_dir.rglob("*.docx")
            if not input_path.name.startswith("~$")  # Skip temporary Word files
        ]

    def _get_output_path(self, relative_path: Path) -> Path:
        """Get output path and ensure directory exists."""
        output_path = self.config.runtime.destination_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path
