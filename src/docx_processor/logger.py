import logging
import sys
from pathlib import Path
from typing import Optional
from custom_formatter import CustomFormatter

class DocxLogger:
    def __init__(self, log_file: Optional[Path] = None, level: int = logging.DEBUG):
        self.logger = logging.getLogger(__name__)
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
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter("%(asctime)s,%(levelname)s,%(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
            self.logger.addHandler(file_handler)
    
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

class ContextLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        ctx = self.extra
        return (
            f"{ctx.get('document_full_path', 'unknown')},"
            f"{ctx.get('document_name', 'unknown')},"
            f"{ctx.get('section', 'unknown')},"
            f"{ctx.get('task', 'unknown')},"
            f"{msg}", kwargs
        )
