"""Logging bootstrap with JSON output and optional Seq sink."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import seqlog

from app.config import Settings


class JsonFormatter(logging.Formatter):
    """Format log records as newline-delimited JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        return json.dumps(log_entry, ensure_ascii=True)


def configure_logging(settings: Settings) -> None:
    """Configure process-wide logging for API and worker processes."""

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(console_handler)

    if settings.seq_url:
        seqlog.log_to_seq(
            server_url=settings.seq_url,
            api_key=settings.seq_api_key.get_secret_value() if settings.seq_api_key else None,
            level=level,
            override_root_logger=False,
            batch_size=10,
            auto_flush_timeout=2,
        )
