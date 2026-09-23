import logging
import sys

# Create logger
logger = logging.getLogger("tld_crawler")
logger.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Console Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# Prevent duplicate handlers when reloaded
if not logger.handlers:
    logger.addHandler(console_handler)