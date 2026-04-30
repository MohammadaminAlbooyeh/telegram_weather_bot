import logging


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    # Avoid duplicate handlers if imported multiple times
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)
    return logger
