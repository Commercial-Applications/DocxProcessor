import logging
import sys
from pathlib import Path
from typing import Optional

from .custom_formatter import CustomFormatter


class DocxLogger:
    CSV_HEADERS = "Timestamp,Level,Path,Document,Section,Module,Location,Table#->Row#,Task,Match,Message\n"

    def __init__(self, log_file: Optional[Path] = None, level: int = logging.DEBUG):
        self._logger = logging.getLogger(__name__)
        self.logger.setLevel(level)
        # Remove any existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Console handler with custom formatter
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(CustomFormatter())
        self.logger.addHandler(console_handler)

        # File handler if log file is specified
        if log_file:
            # Change extension to .csv
            log_file = log_file.with_suffix(".csv")

        # Write headers if file doesn't exist or is empty
        if not log_file.exists() or log_file.stat().st_size == 0:
            log_file.write_text(self.CSV_HEADERS, encoding="utf-8")

            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s,%(levelname)s,%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            )
            self.logger.addHandler(file_handler)

    @property
    def logger(self):
        return self._logger

    def isEnabledFor(self, level: int) -> bool:
        return self.logger.isEnabledFor(level)

    def debug(self, message: str) -> None:
        self.logger.debug(message)

    def info(self, message: str) -> None:
        self.logger.info(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def error(self, message: str) -> None:
        self.logger.error(message)

    def exception(self, message: str) -> None:
        self.logger.exception(message)

    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        self.logger.log(level, msg, *args, **kwargs)
