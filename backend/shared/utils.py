import logging
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_logger(name: str) -> logging.Logger:
    """Configures and returns a standard logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        # Console Handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

def get_config(key: str, default: str = "") -> str:
    """Retrieves an environment variable config value."""
    return os.getenv(key, default)
