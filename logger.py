import logging
import sys
from pathlib import Path
from typing import Optional
from CustomFormatter import CustomFormatter

class DocxLogger:
    def __init__(self, log_file: Optional[Path] = None, level: int = logging.INFO):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level)
        
        # Remove any existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Console handler with custom formatter
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(CustomFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler if log file is specified
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.WARNING)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
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