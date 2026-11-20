# src/docx_processor/processors/batch.py
import logging
import logging.handlers
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Tuple

from docx_processor.logger import ContextLoggerAdapter
from .document import DocumentProcessor

DEFAULT_LOG_CONTEXT = {
    "document_name": "",
    "document_full_path": "",
    "section": "",
    "module": "",
    "location": "No Heading",
    "table_row": "",
    "match": "False",
}

# Set in each worker process by _init_worker, then reused for every document that worker handles.
_worker_processor: Optional[DocumentProcessor] = None


def _init_worker(config, log_queue, log_level: int) -> None:
    """Worker-process initialiser: route logging to the parent through a queue and build one processor."""
    global _worker_processor
    logger = logging.getLogger("docx_processor.worker")
    logger.handlers[:] = [logging.handlers.QueueHandler(log_queue)]
    logger.setLevel(log_level)
    logger.propagate = False
    _worker_processor = DocumentProcessor(config, ContextLoggerAdapter(logger, dict(DEFAULT_LOG_CONTEXT)))


def _process_in_worker(job: Tuple[Path, Path]) -> bool:
    input_path, output_path = job
    return _worker_processor.process_document(input_path, output_path)


class BatchProcessor:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.workers = config.runtime.workers
        self.find_only = config.runtime.find_only
        self.processed_count = 0
        self.failed_count = 0
        self.start_time = None

    def process_all_docx(self) -> None:
        """Process all documents one at a time in this process."""
        self._start()
        self._run_sequential(self._get_jobs())
        self._report()

    def process_all_docx_parallel(self) -> None:
        """Process documents in parallel worker processes.

        python-docx work is pure Python, so threads cannot run it in parallel (the GIL); separate
        processes can. Falls back to sequential processing for a single worker or document.
        """
        self._start()
        jobs = self._get_jobs()
        workers = min(self.workers, len(jobs))
        if workers <= 1:
            self._run_sequential(jobs)
        else:
            self._run_parallel(jobs, workers)
        self._report()

    # ------------------------------------------------------------------ internals

    def _start(self) -> None:
        self.start_time = time.time()
        self.processed_count = 0
        self.failed_count = 0

    def _count(self, ok: bool) -> None:
        if ok:
            self.processed_count += 1
        else:
            self.failed_count += 1

    def _run_sequential(self, jobs: List[Tuple[Path, Path]]) -> None:
        processor = DocumentProcessor(self.config, self.logger)
        for input_path, output_path in jobs:
            self._count(processor.process_document(input_path, output_path))

    def _run_parallel(self, jobs: List[Tuple[Path, Path]], workers: int) -> None:
        base_logger = self._stdlib_logger()
        log_queue = multiprocessing.Queue()
        # Log records from the workers are written by this process's existing console/CSV handlers.
        listener = logging.handlers.QueueListener(log_queue, *base_logger.handlers, respect_handler_level=True)
        listener.start()
        try:
            with ProcessPoolExecutor(
                max_workers=workers,
                initializer=_init_worker,
                initargs=(self.config, log_queue, base_logger.getEffectiveLevel()),
            ) as pool:
                futures = {pool.submit(_process_in_worker, job): job for job in jobs}
                for future in as_completed(futures):
                    try:
                        self._count(future.result())
                    except Exception as e:  # e.g. a worker process crashed
                        self.failed_count += 1
                        self.logger.error(f"Failed to process {futures[future][0]}: {e}")
        finally:
            listener.stop()

    def _stdlib_logger(self) -> logging.Logger:
        """The logging.Logger underneath the ContextLoggerAdapter / DocxLogger wrappers."""
        logger = self.logger
        while not isinstance(logger, logging.Logger):
            logger = logger.logger
        return logger

    def _report(self) -> None:
        total_time = time.time() - self.start_time
        self.logger.info(
            f"Processing complete. Documents processed: {self.processed_count}, failed: {self.failed_count}"
        )
        self.logger.info(f"Total processing time: {total_time:.2f} seconds")

    def _get_jobs(self) -> List[Tuple[Path, Path]]:
        source_dir = self.config.runtime.source_dir
        return [(path, self._get_output_path(path.relative_to(source_dir))) for path in self._get_document_paths()]

    def _get_document_paths(self):
        """Get all valid document paths."""
        return [
            input_path
            for input_path in self.config.runtime.source_dir.rglob("*.docx")
            if not input_path.name.startswith("~$")  # Skip temporary Word files
        ]

    def _get_output_path(self, relative_path: Path) -> Path:
        """Get output path, creating its directory only when documents will be written."""
        output_path = self.config.runtime.destination_dir / relative_path
        if not self.find_only:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path
