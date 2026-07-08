"""Structured JSON logging helpers."""
import json
import logging
import sys
import time
from typing import Optional

from config import get_settings


class JsonFormatter(logging.Formatter):
    RESERVED = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "taskName", "message",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def log_event(
    logger: logging.Logger,
    message: str,
    *,
    action: Optional[str] = None,
    job_id: Optional[str] = None,
    phone: Optional[str] = None,
    latency_ms: Optional[float] = None,
    level: int = logging.INFO,
    **extra,
) -> None:
    fields = {
        "action": action,
        "job_id": job_id,
        "phone": phone,
        "latency_ms": latency_ms,
        "business_id": get_settings().business_id,
        **extra,
    }
    logger.log(level, message, extra={k: v for k, v in fields.items() if v is not None})


class Timer:
    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.latency_ms = round((time.perf_counter() - self._start) * 1000, 2)
        return False
