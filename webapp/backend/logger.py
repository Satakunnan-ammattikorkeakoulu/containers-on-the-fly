import logging
from database import Base
from helpers.server import orm_to_dict
from os import linesep

class CustomLogger(logging.Logger):
  '''
  Custom logger that prints database objects as dictionaries.

  Example usage:
    from logger import log
    log.info("Hello world!")
    log.info(myDatabaseObject)
    log.warning("Something went wrong!")    
  '''
  def __init__(self, name):
    super().__init__(name)

  def get_msg(self, msg):
    try:
      # Print database objects as dictionaries
      if isinstance(msg, Base):
        return f"{linesep}{msg}{linesep}{linesep}{orm_to_dict(msg)}"
      else:
        return f"{linesep}{msg}"
    except:
      return f"{linesep}{msg}"

  def debug(self, msg, *args, **kwargs):
    super().debug(self.get_msg(msg), *args, **kwargs)
  def info(self, msg, *args, **kwargs):
    super().info(self.get_msg(msg), *args, **kwargs)
  def warning(self, msg, *args, **kwargs):
    super().warning(self.get_msg(msg), *args, **kwargs)
  def error(self, msg, *args, **kwargs):
    super().error(self.get_msg(msg), *args, **kwargs)
  def critical(self, msg, *args, **kwargs):
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
    log_color = self.format_dict.get(record.levelno)
    reset_color = "\033[0m"
    gray_color = "\033[37m"
    formatter = f"{log_color}%(levelname)s - %(asctime)s - %(filename)s:%(lineno)d:{reset_color} %(message)s{linesep}"
    self._style._fmt = formatter
    return super().format(record)

# Set our custom logger as the default logger
logging.setLoggerClass(CustomLogger)

# Create a custom logger
log = logging.getLogger('global_logger')

# Set the level of logger. It can be DEBUG, INFO, WARNING, ERROR or CRITICAL
# TODO: From settings
log.setLevel(logging.DEBUG)

# Create handlers
# TODO: from settings
console_handler = logging.StreamHandler()  # logs to console
#file_handler = logging.FileHandler('logfile.log') # logs to a file

# Set the level of handler
console_handler.setLevel(logging.DEBUG)
#file_handler.setLevel(logging.DEBUG)

# Create formatter and add it to handlers
formatter = ColoredFormatter()
console_handler.setFormatter(formatter)
#file_handler.setFormatter(formatter)

# Add handlers to the logger
log.addHandler(console_handler)
#log.addHandler(file_handler)