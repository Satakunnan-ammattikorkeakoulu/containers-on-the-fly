"""Simple logging module for the container server daemon.

Provides a colored console logger without database dependencies.

Usage:
    from helpers.logger import log
    log.info("Hello world!")
"""

import logging


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


# Create logger
log = logging.getLogger('container_server')

# Read log level from settings if available
_LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_configured_level = "DEBUG"
try:
    from helpers.settings_handler import settings_handler
    _configured_level = settings_handler.get_setting("app.logLevel") or "DEBUG"
except Exception:
    pass

log.setLevel(_LOG_LEVEL_MAP.get(_configured_level.upper(), logging.INFO))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(_LOG_LEVEL_MAP.get(_configured_level.upper(), logging.INFO))
console_handler.setFormatter(ColoredFormatter())
log.addHandler(console_handler)
