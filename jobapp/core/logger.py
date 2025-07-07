import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

DEFAULT_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

def get_logger(name: str = __name__, level: str = DEFAULT_LEVEL, log_file: Optional[Path] = None):
    """
    Configures and returns a logger.
    
    If log_file is provided, it creates a dedicated file handler for that file.
    Otherwise, it uses only a console handler (no default file logging).
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times, which can cause duplicate log entries
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.setLevel(level)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s]: %(message)s')

    if log_file:
        # Dedicated file handler for a specific job log
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    
    # Always add a console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger.propagate = False
    return logger 