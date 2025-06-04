"""
Configuration constants and defaults.
"""
from pathlib import Path
import logging

# Default configuration values
DEFAULT_CONFIG_FILE = Path("config.yml")
DEFAULT_WORKERS = 4

# Logging levels
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
DEFAULT_LOG_LEVEL = LOG_LEVEL_WARNING

# Mapping of string levels to numeric values
LOG_LEVEL_MAP = {
    LOG_LEVEL_DEBUG: logging.DEBUG,      # 10
    LOG_LEVEL_INFO: logging.INFO,        # 20
    LOG_LEVEL_WARNING: logging.WARNING,  # 30
    LOG_LEVEL_ERROR: logging.ERROR       # 40
}

LOG_LEVELS = [LOG_LEVEL_DEBUG, LOG_LEVEL_INFO, LOG_LEVEL_WARNING, LOG_LEVEL_ERROR]

__all__ = [
    'DEFAULT_CONFIG_FILE',
    'DEFAULT_WORKERS',
    'DEFAULT_LOG_LEVEL',
    'LOG_LEVELS',
    'LOG_LEVEL_MAP'
]