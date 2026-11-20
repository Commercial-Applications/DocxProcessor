import logging


class CustomFormatter(logging.Formatter):
    """Coloured, human-readable console output.

    Records from ContextLoggerAdapter are shown as
    ``HH:MM:SS LEVEL   document.docx [Section / H1 Heading / table 2|3] message``;
    the CSV log file keeps the full comma-separated row. Other records use the plain format.
    """

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    blue = "\x1b[34;20m"
    green = "\x1b[32;20m"
    reset = "\x1b[0m"

    LOG_FORMAT = "%(asctime)s,%(levelname)s,%(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    TIME_FORMAT = "%H:%M:%S"

    COLOURS = {
        logging.DEBUG: grey,
        logging.INFO: blue,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red,
    }
    FORMATS = {
        logging.DEBUG: grey + LOG_FORMAT + reset,
        logging.INFO: blue + LOG_FORMAT + reset,
        logging.WARNING: yellow + LOG_FORMAT + reset,
        logging.ERROR: red + LOG_FORMAT + reset,
        logging.CRITICAL: bold_red + LOG_FORMAT + reset,
    }

    # Context values that carry no information for a reader.
    _EMPTY = {"", "NA", "unknown"}

    def __init__(self):
        super().__init__(self.LOG_FORMAT, datefmt=self.DATE_FORMAT)
        # Build one formatter per level up front instead of a new one for every record.
        self._formatters = {
            level: logging.Formatter(fmt, datefmt=self.DATE_FORMAT) for level, fmt in self.FORMATS.items()
        }

    def format(self, record):
        ctx = getattr(record, "docx_ctx", None)
        if ctx is None:
            formatter = self._formatters.get(record.levelno)
            return formatter.format(record) if formatter else super().format(record)
        return self._readable(record, ctx)

    def _readable(self, record, ctx) -> str:
        table_row = ctx.get("table_row") or ""
        where = [ctx.get("section") or "", ctx.get("location") or "", f"table {table_row}" if table_row else ""]
        where = " / ".join(part for part in where if part not in self._EMPTY)
        document = ctx.get("document_name") or ""

        line = f"{self.formatTime(record, self.TIME_FORMAT)} {record.levelname:<7} "
        if document not in self._EMPTY:
            line += f"{document} "
        if where:
            line += f"[{where}] "
        line += getattr(record, "docx_msg", record.getMessage())

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            line += "\n" + record.exc_text
        colour = self.COLOURS.get(record.levelno, "")
        return f"{colour}{line}{self.reset}" if colour else line
