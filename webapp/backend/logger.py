"""Custom logging module with colored output and ORM object formatting.

Provides a custom logger class that automatically converts SQLAlchemy ORM
objects to dictionaries for readable log output, and a colored formatter
that applies ANSI color codes based on log level.

Usage:
    from logger import log
    log.info("Hello world!")
    log.info(my_database_object)
"""

import logging
from database import Base
from helpers.server import orm_to_dict
from os import linesep

class CustomLogger(logging.Logger):
  """Custom logger that automatically formats SQLAlchemy ORM objects as dictionaries.

  Example usage::

      from logger import log
      log.info("Hello world!")
      log.info(myDatabaseObject)
      log.warning("Something went wrong!")
  """

  def __init__(self, name):
    super().__init__(name)

  def get_msg(self, msg):
    """Format a log message, converting ORM objects to readable dicts.

    Args:
        msg: The log message or SQLAlchemy ORM object to format.

    Returns:
        Formatted string with a leading newline for readability.
    """
    try:
      if isinstance(msg, Base):
        return f"{msg} {orm_to_dict(msg)}"
      else:
        return str(msg)
    except Exception:
      return str(msg)

  def debug(self, msg, *args, **kwargs):
    """Log a DEBUG-level message with ORM formatting."""
    super().debug(self.get_msg(msg), *args, **kwargs)

  def info(self, msg, *args, **kwargs):
    """Log an INFO-level message with ORM formatting."""
    super().info(self.get_msg(msg), *args, **kwargs)

  def warning(self, msg, *args, **kwargs):
    """Log a WARNING-level message with ORM formatting."""
    super().warning(self.get_msg(msg), *args, **kwargs)

  def error(self, msg, *args, **kwargs):
    """Log an ERROR-level message with ORM formatting."""
    super().error(self.get_msg(msg), *args, **kwargs)

  def critical(self, msg, *args, **kwargs):
    """Log a CRITICAL-level message with ORM formatting."""
    super().critical(self.get_msg(msg), *args, **kwargs)

class ColoredFormatter(logging.Formatter):
  """Logging Formatter to add colors based on the log level."""

  format_dict = {
    logging.DEBUG: "\033[34m",       # Blue
    logging.INFO: "\033[92m",        # Green
    logging.WARNING: "\033[93m",     # Yellow
    logging.ERROR: "\033[91m",       # Red
    logging.CRITICAL: "\033[1;91m",  # Bright red
  }

  def format(self, record):
    """Format a log record with ANSI color codes based on log level.

    Args:
        record: The log record to format.

    Returns:
        Colored, formatted log string.
    """
    log_color = self.format_dict.get(record.levelno)
    reset_color = "\033[0m"
    formatter = f"{log_color}%(levelname)s:{reset_color} %(message)s"
    self._style._fmt = formatter
    return super().format(record)

# Set our custom logger as the default logger
logging.setLoggerClass(CustomLogger)

# Create a custom logger
log = logging.getLogger('global_logger')

# Read log level from settings (file-based, so no DB access needed)
_LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_configured_level = "DEBUG"
try:
    from settings_handler import settings_handler
    _configured_level = settings_handler.get_setting("app.logLevel") or "DEBUG"
except Exception:
    pass  # Fall back to DEBUG if settings not yet available

log.setLevel(_LOG_LEVEL_MAP.get(_configured_level.upper(), logging.INFO))

# Create handlers (console only — pm2 handles log persistence to disk)
console_handler = logging.StreamHandler()
console_handler.setLevel(_LOG_LEVEL_MAP.get(_configured_level.upper(), logging.INFO))

# Create formatter and add it to handlers
formatter = ColoredFormatter()
console_handler.setFormatter(formatter)

# Add handlers to the logger
log.addHandler(console_handler)