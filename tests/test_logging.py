from __future__ import annotations

import json
import logging

from app.logging import JsonFormatter


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
