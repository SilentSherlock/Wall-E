from __future__ import annotations

from logging.handlers import TimedRotatingFileHandler
import logging
from pathlib import Path


def configure_logging() -> None:
    """Configure warning/error logging to daily-rotated files under ./logs."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)

    project_root = Path(__file__).resolve().parents[2]
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s %(name)s [%(levelname)s] %(message)s")
    file_handler = TimedRotatingFileHandler(
        filename=str(logs_dir / "walle.log"),
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.WARNING)
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    root_logger.setLevel(logging.WARNING)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
