"""
Structured logging configuration for RehabAI backend.
Provides consistent, machine-parseable logs for production monitoring.
"""

import logging
import sys
import json
import traceback
from datetime import datetime, timezone
from typing import Any, Optional
from functools import wraps
import time
import uuid

class StructuredFormatter(logging.Formatter):
    """
    Formats log records as structured JSON for machine parsing.
    Also supports human-readable mode for development.
    """

    def __init__(self, human_readable: bool = False):
        super().__init__()
        self.human_readable = human_readable
        # Colors for terminal output
        self.colors = {
            'DEBUG': '\033[36m',     # Cyan
            'INFO': '\033[32m',      # Green
            'WARNING': '\033[33m',   # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m',  # Magenta
            'RESET': '\033[0m',
        }

    def format(self, record: logging.LogRecord) -> str:
        if self.human_readable:
            return self._format_human(record)
        return self._format_json(record)

    def _format_json(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context if available
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        if hasattr(record, 'session_id'):
            log_data["session_id"] = record.session_id
        if hasattr(record, 'duration_ms'):
            log_data["duration_ms"] = round(record.duration_ms, 2)
        if hasattr(record, 'status_code'):
            log_data["status_code"] = record.status_code
        if hasattr(record, 'error'):
            log_data["error"] = record.error
            log_data["traceback"] = record.traceback

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'lineno', 'module', 'msecs', 'message', 'pathname',
                          'process', 'processName', 'relativeCreated', 'stack_info',
                          'exc_info', 'exc_text', 'thread', 'threadName', 'message',
                          'request_id', 'user_id', 'session_id', 'duration_ms', 'status_code',
                          'error', 'traceback'):
                if not key.startswith('_'):
                    log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            log_data["exception_message"] = str(record.exc_info[1]) if record.exc_info[1] else None

        return json.dumps(log_data, ensure_ascii=False, default=str)

    def _format_human(self, record: logging.LogRecord) -> str:
        color = self.colors.get(record.levelname, '')
        reset = self.colors['RESET']

        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level = f"{color}{record.levelname:8}{reset}"

        parts = [f"[{timestamp}] {level}"]

        # Add context
        if hasattr(record, 'request_id'):
            parts.append(f"[{record.request_id[:8]}]")
        if hasattr(record, 'user_id'):
            parts.append(f"[{record.user_id[:8]}]")

        parts.append(f"{record.getMessage()}")

        # Add duration if available
        if hasattr(record, 'duration_ms'):
            parts.append(f"({record.duration_ms:.1f}ms)")

        # Add error if present
        if hasattr(record, 'error'):
            parts.append(f"❌ {record.error}")

        return " ".join(parts)


class ContextAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds persistent context to log messages.
    """

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        # Merge extra kwargs with stored extra
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)

        # Also merge into record kwargs for _format_json
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        for key, value in self.extra.items():
            if key not in kwargs['extra']:
                kwargs['extra'][key] = value

        return msg, kwargs


def setup_logging(
    level: str = "INFO",
    human_readable: bool = True,
    log_file: Optional[str] = None
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        human_readable: Use colored terminal output (True for dev, False for prod)
        log_file: Optional file path for JSON log output
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter(human_readable=human_readable))
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.addHandler(console_handler)

    # File handler (JSON format)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(StructuredFormatter(human_readable=False))
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

    # Suppress noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


def get_logger(name: str, **context: Any) -> ContextAdapter:
    """
    Get a logger with optional persistent context.

    Usage:
        logger = get_logger("rehabai.inference", user_id="user123")
        logger.info("Processing request")  # Includes user_id in all logs
    """
    base_logger = logging.getLogger(name)
    return ContextAdapter(base_logger, context)


class RequestLogger:
    """
    Context manager for logging HTTP requests with timing.

    Usage:
        with RequestLogger(logger, request_id="req123") as rl:
            # Process request
            rl.set_status(200)
    """

    def __init__(
        self,
        logger: logging.Logger,
        request_id: Optional[str] = None,
        method: str = "GET",
        path: str = "/",
        **context
    ):
        self.logger = logger
        self.request_id = request_id or str(uuid.uuid4())
        self.method = method
        self.path = path
        self.context = context
        self.start_time = time.perf_counter()
        self.status_code: Optional[int] = None
        self.error: Optional[str] = None

    def __enter__(self) -> 'RequestLogger':
        extra = {
            'request_id': self.request_id,
            'method': self.method,
            'path': self.path,
            'duration_ms': 0,  # Will be updated
            **self.context
        }
        self.logger.info(
            f"→ {self.method} {self.path}",
            extra=extra
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000

        extra = {
            'request_id': self.request_id,
            'method': self.method,
            'path': self.path,
            'duration_ms': duration_ms,
            **self.context
        }

        if self.status_code:
            extra['status_code'] = self.status_code

        if exc_type:
            extra['error'] = str(exc_val)
            extra['traceback'] = traceback.format_exception(exc_type, exc_val, exc_tb)
            self.logger.error(
                f"✗ {self.method} {self.path} [{self.status_code or 'ERR'}] {duration_ms:.1f}ms",
                extra=extra,
                exc_info=(exc_type, exc_val, exc_tb)
            )
        else:
            self.logger.info(
                f"✓ {self.method} {self.path} [{self.status_code or '?'}] {duration_ms:.1f}ms",
                extra=extra
            )

        return False  # Don't suppress exceptions

    def set_status(self, code: int) -> None:
        self.status_code = code

    def set_error(self, error: str) -> None:
        self.error = error


def log_function_call(logger: logging.Logger):
    """
    Decorator to automatically log function calls with timing.

    Usage:
        @log_function_call(logger)
        def my_function(arg1, arg2):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            start_time = time.perf_counter()

            logger.debug(f"Calling {func_name}({args}, {kwargs})")

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(f"{func_name} completed in {duration_ms:.2f}ms")
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"{func_name} failed after {duration_ms:.2f}ms: {e}",
                    extra={'error': str(e), 'function': func_name}
                )
                raise

        return wrapper
    return decorator
