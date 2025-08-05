"""
Logging package initialization.
"""

from .context import ContextLoggerAdapter
from .custom_formatter import CustomFormatter
from .docx import DocxLogger


def setup_logger(config):
    """Create and configure a logger instance."""
    from docx_processor.config.constants import LOG_LEVEL_MAP
    import logging

    base_level = LOG_LEVEL_MAP[config.runtime.log_level]

    if config.runtime.verbose:
        # Decrease level by 10 for each verbose flag (-v)
        adjusted_level = max(logging.DEBUG, base_level - (config.runtime.verbose * 10))
        config.runtime.log_level = logging.getLevelName(adjusted_level)

    logger = DocxLogger(log_file=config.runtime.log_file, level=LOG_LEVEL_MAP[config.runtime.log_level])

    return ContextLoggerAdapter(
        logger,
        {
            "document_name": "",
            "document_full_path": "",
            "section": "",
            "module": "",
            "location": "No Heading",
            "table_row": "",
            "match": "False",
        },
    )


__all__ = ["DocxLogger", "setup_logger", "ContextLoggerAdapter", "CustomFormatter"]
