"""
Structured logging with field redaction.
Redacts: password, token, authorization, embedding, secret_key, jwt_secret
"""
import json
import logging
import sys
from typing import Any, Dict

REDACTED_FIELDS = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "access_token",
        "authorization",
        "embedding",
        "secret_key",
        "jwt_secret",
        "x-api-key",
    }
)


class RedactingFilter(logging.Filter):
    """Logging filter that replaces sensitive field values with '[REDACTED]'."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        if isinstance(record.msg, dict):
            record.msg = self._redact(record.msg)
        elif isinstance(record.msg, str) and record.args:
            # Attempt redaction when extra dict is passed
            if isinstance(record.args, dict):
                record.args = self._redact(record.args)  # type: ignore[assignment]
        return True

    def _redact(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: "[REDACTED]" if k.lower() in REDACTED_FIELDS else self._redact(v)
                for k, v in data.items()
            }
        if isinstance(data, list):
            return [self._redact(item) for item in data]
        return data


class JsonFormatter(logging.Formatter):
    """Emit one JSON line per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra_keys = {
            k: v
            for k, v in record.__dict__.items()
            if k not in logging.LogRecord.__dict__
            and not k.startswith("_")
            and k
            not in (
                "args",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "message",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "taskName",
                "thread",
                "threadName",
            )
        }
        payload.update(extra_keys)
        return json.dumps(payload, default=str)


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root logger with JSON formatting and redaction filter."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactingFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # Remove any existing handlers
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
