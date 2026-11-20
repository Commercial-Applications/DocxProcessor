import csv
import logging
from io import StringIO

# Context fields, in the column order of DocxLogger.CSV_HEADERS (after Timestamp and Level).
CONTEXT_FIELDS = ("document_full_path", "document_name", "section", "module", "location", "table_row", "task", "match")


class ContextLoggerAdapter(logging.LoggerAdapter):
    """Prefix each message with the current document context, formatted as CSV fields."""

    def process(self, msg, kwargs):
        ctx = self.extra
        fields = [ctx.get(name, "unknown") for name in CONTEXT_FIELDS]
        fields.append(msg)
        # One CSV writer per log line (previously one per field); falsy values become empty fields.
        output = StringIO()
        csv.writer(output, quoting=csv.QUOTE_MINIMAL).writerow([str(f) if f else "" for f in fields])
        return output.getvalue().rstrip("\r\n"), kwargs
