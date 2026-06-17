from __future__ import annotations

import json
import logging
from unittest.mock import patch

from app.config import Settings
from app.logging import JsonFormatter
from app.logging import configure_logging


def test_json_formatter_includes_standard_fields() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello world",
        args=(),
        exc_info=None,
    )

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert payload["message"] == "hello world"
    assert "timestamp" in payload


def test_json_formatter_includes_structured_extras() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.WARNING,
        pathname=__file__,
        lineno=20,
        msg="dispatch failed",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "corr-123"
    record.dispatch_id = 42
    record.retry_count = 2
    record.final_status = "PENDING"

    payload = json.loads(formatter.format(record))

    assert payload["correlation_id"] == "corr-123"
    assert payload["dispatch_id"] == 42
    assert payload["retry_count"] == 2
    assert payload["final_status"] == "PENDING"


def test_configure_logging_adds_seq_handler_when_seq_enabled() -> None:
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    seq_handler = logging.NullHandler()
    settings = Settings(SEQ_URL="http://seq.local:5341", SEQ_API_KEY="test-key")

    with patch("app.logging.seqlog.log_to_seq", return_value=seq_handler) as log_to_seq_mock:
        configure_logging(settings)

    assert log_to_seq_mock.called
    assert any(handler is seq_handler for handler in root_logger.handlers)


def test_configure_logging_routes_uvicorn_loggers_to_root() -> None:
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    settings = Settings()
    configure_logging(settings)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(logger_name)
        assert logger.propagate is True
        assert logger.handlers == []
