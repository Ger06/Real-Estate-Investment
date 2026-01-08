"""
Logging configuration
"""
import logging
import sys
from pathlib import Path

from app.core.config import settings


def setup_logging() -> None:
    """Configure application logging"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    log_level = getattr(logging, settings.LOG_LEVEL.upper())
    
    if settings.LOG_FORMAT == "json":
        # JSON logging for production
        try:
            import json_log_formatter
            
            formatter = json_log_formatter.JSONFormatter()
            
            json_handler = logging.FileHandler(log_dir / "app.json")
            json_handler.setFormatter(formatter)
            
            logging.basicConfig(
                level=log_level,
                handlers=[json_handler, logging.StreamHandler(sys.stdout)]
            )
        except ImportError:
            # Fallback to console logging
            setup_console_logging(log_level)
    else:
        # Console logging for development
        setup_console_logging(log_level)
    
    # Set third-party loggers to WARNING
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def setup_console_logging(log_level: int) -> None:
    """Setup console logging with colored output"""
    
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=log_level,
        handlers=[console_handler, file_handler]
    )
