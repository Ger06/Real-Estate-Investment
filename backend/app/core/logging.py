"""
Logging configuration
"""
import logging
import sys
from pathlib import Path

from app.core.config import settings


def setup_logging() -> None:
    """Configure application logging"""

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_level = getattr(logging, settings.LOG_LEVEL.upper())
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicating handlers on uvicorn --reload
    if root_logger.handlers:
        return

    if settings.LOG_FORMAT == "json":
        try:
            import json_log_formatter
            formatter = json_log_formatter.JSONFormatter()
            json_handler = logging.FileHandler(log_dir / "app.json")
            json_handler.setFormatter(formatter)
            root_logger.addHandler(json_handler)
            root_logger.addHandler(logging.StreamHandler(sys.stdout))
        except ImportError:
            _setup_console_handlers(root_logger, log_level)
    else:
        _setup_console_handlers(root_logger, log_level)

    # Reduce noise from external libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def _setup_console_handlers(root_logger: logging.Logger, log_level: int) -> None:
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def setup_console_logging(log_level: int) -> None:
    """Legacy alias kept for compatibility"""
    _setup_console_handlers(logging.getLogger(), log_level)
