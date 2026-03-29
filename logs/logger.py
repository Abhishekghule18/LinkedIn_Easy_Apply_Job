import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path

# Custom SUCCESS Level
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")

def success(self, message, *args, **kws):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kws)

logging.Logger.success = success

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

class CustomFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: "[DEBUG] %(asctime)s - %(message)s",
        logging.INFO: "[INFO] %(asctime)s - %(message)s",
        logging.WARNING: "[WARNING] %(asctime)s - %(message)s",
        logging.ERROR: "[ERROR] %(asctime)s - %(message)s",
        SUCCESS_LEVEL_NUM: "[SUCCESS] %(asctime)s - %(message)s"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, "[INFO] %(asctime)s - %(message)s")
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

def setup_logger():
    logger = logging.getLogger("LinkedInBot")
    logger.setLevel(logging.DEBUG)
    
    if logger.handlers:
        return logger

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(CustomFormatter())
    
    # App file handler (Rotating, max 5MB)
    app_handler = RotatingFileHandler(LOGS_DIR / "app.log", maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(CustomFormatter())

    # Error file handler (Rotating, max 5MB)
    error_handler = RotatingFileHandler(LOGS_DIR / "error.log", maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(CustomFormatter())

    logger.addHandler(ch)
    logger.addHandler(app_handler)
    logger.addHandler(error_handler)
    
    return logger

app_logger = setup_logger()

# Direct export methods for ease of use
def log_info(msg: str):
    app_logger.info(msg)

def log_error(msg: str):
    app_logger.error(msg)
    
def log_success(msg: str):
    app_logger.success(msg)

def log_warning(msg: str):
    app_logger.warning(msg)
    
def log_debug(msg: str):
    app_logger.debug(msg)
