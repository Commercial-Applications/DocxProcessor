import logging
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
