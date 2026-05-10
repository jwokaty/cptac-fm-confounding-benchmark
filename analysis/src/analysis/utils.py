"""
utils.py

Shared utilities for the analysis project.
"""

from datetime import datetime
import logging
from pathlib import Path


def get_logger(name: str, log_dir: Path) -> logging.Logger:
    """
    Create a logger that writes to both the terminal and a timestamped log file.

    Args:
        name:    logger name, typically the script name (e.g. "pool_to_case_id")
        log_dir: directory to write log files to
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
