import logging


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    blue = "\x1b[34;20m"
    green = "\x1b[32;20m"
    reset = "\x1b[0m"

    LOG_FORMAT = "%(asctime)s,%(levelname)s,%(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    FORMATS = {
        logging.DEBUG: grey + LOG_FORMAT + reset,
        logging.INFO: blue + LOG_FORMAT + reset,
        logging.WARNING: yellow + LOG_FORMAT + reset,
        logging.ERROR: red + LOG_FORMAT + reset,
        logging.CRITICAL: bold_red + LOG_FORMAT + reset,
    }

    def __init__(self):
        super().__init__(self.LOG_FORMAT, datefmt=self.DATE_FORMAT)
        # Build one formatter per level up front instead of a new one for every record.
        self._formatters = {
            level: logging.Formatter(fmt, datefmt=self.DATE_FORMAT) for level, fmt in self.FORMATS.items()
        }

    def format(self, record):
        if not hasattr(record, "location"):
            record.location = "No Heading"
        formatter = self._formatters.get(record.levelno)
        return formatter.format(record) if formatter else super().format(record)
