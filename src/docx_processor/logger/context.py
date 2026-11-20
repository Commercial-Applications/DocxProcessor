import csv
import logging
from io import StringIO

# Context fields, in the column order of DocxLogger.CSV_HEADERS (after Timestamp and Level).
CONTEXT_FIELDS = ("document_full_path", "document_name", "section", "module", "location", "table_row", "task", "match")


class ContextLoggerAdapter(logging.LoggerAdapter):
    """Prefix each message with the current document context, formatted as CSV fields.

    The CSV text becomes the record's message (written as-is to the CSV log file). The raw message
    and a snapshot of the context are also attached to the record as ``docx_msg`` and ``docx_ctx``,
    so the console formatter can print a readable line instead of the CSV row.
    """

    def process(self, msg, kwargs):
        ctx = self.extra
        fields = [ctx.get(name, "unknown") for name in CONTEXT_FIELDS]
        fields.append(msg)
        # One CSV writer per log line (previously one per field); falsy values become empty fields.
        output = StringIO()
        csv.writer(output, quoting=csv.QUOTE_MINIMAL).writerow([str(f) if f else "" for f in fields])
        kwargs["extra"] = {**kwargs.get("extra", {}), "docx_ctx": dict(ctx), "docx_msg": str(msg)}
        return output.getvalue().rstrip("\r\n"), kwargs
