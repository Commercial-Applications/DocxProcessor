import csv
import logging
from io import StringIO


class ContextLoggerAdapter(logging.LoggerAdapter):
    def _escape_csv(self, text):
        if not text:
            return ""
        output = StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([str(text)])
        return output.getvalue().rstrip("\r\n")

    def process(self, msg, kwargs):
        ctx = self.extra
        # Escape each field
        fields = [
            self._escape_csv(ctx.get("document_full_path", "unknown")),
            self._escape_csv(ctx.get("document_name", "unknown")),
            self._escape_csv(ctx.get("section", "unknown")),
            self._escape_csv(ctx.get("module", "unknown")),
            self._escape_csv(ctx.get("location", "unknown")),
            self._escape_csv(ctx.get("task", "unknown")),
            self._escape_csv(ctx.get("match", "unknown")),
            self._escape_csv(msg),
        ]
        return (",".join(fields), kwargs)
