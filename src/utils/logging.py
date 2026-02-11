"""
Logging utilities for Diogenes.

Provides structured logging with consistent formatting across all modules.
Supports both human-readable and JSON-structured output.
"""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.config import get_settings


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for production observability.

    Each log record is emitted as a single-line JSON object with fields:
    ``timestamp``, ``level``, ``logger``, ``message``, plus optional
    ``exc_info`` and any extra context attached via :class:`LogContext`.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Include any extra context attributes set via LogContext
        for attr in ("session_id", "query", "request_id", "user_id"):
            val = getattr(record, attr, None)
            if val is not None:
                log_entry[attr] = val

        return json.dumps(log_entry, default=str)


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to config value.
        format_string: Log format string. Defaults to config value.
        log_file: Optional file to write logs to. Defaults to config value.
    """
    settings = get_settings()
    
    level = level or settings.logging.level
    format_string = format_string or settings.logging.format
    log_file = log_file or settings.logging.file
    use_json = settings.logging.json_format
    
    # Pick formatter
    if use_json:
        formatter: logging.Formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(format_string)
    
    # Create handlers
    handlers: list[logging.Handler] = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler (if configured)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True,
    )
    
    # Set third-party loggers to WARNING to reduce noise
    for logger_name in ["httpx", "httpcore", "urllib3", "asyncio"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name, typically __name__ of the module.
        
    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for adding extra context to log messages.
    
    Usage:
        with LogContext(logger, session_id="abc123", query="test"):
            logger.info("Processing request")
    """
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        old_factory = logging.getLogRecordFactory()
        context = self.context
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            for key, value in context.items():
                setattr(record, key, value)
            return record
        
        self.old_factory = old_factory
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, *args):
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)
