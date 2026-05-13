"""Unit tests for the logging configuration."""

from __future__ import annotations

import io
import json
import logging

from greenhouse.logging_config import JsonFormatter, configure_logging


def test_json_formatter_emits_valid_json() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="greenhouse.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    payload = json.loads(formatter.format(record))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "greenhouse.test"
    assert payload["message"] == "hello world"
    assert "ts" in payload


def test_json_formatter_promotes_ctx_fields() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="greenhouse.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="ctx",
        args=(),
        exc_info=None,
    )
    # Simulate logger.info("ctx", extra={"ctx_user": "alice"})
    record.ctx_user = "alice"
    payload = json.loads(formatter.format(record))
    assert payload["user"] == "alice"


def test_configure_logging_replaces_handlers() -> None:
    """Calling configure_logging repeatedly must not stack handlers."""
    configure_logging(level="WARNING", fmt="json")
    first_count = len(logging.getLogger().handlers)
    configure_logging(level="WARNING", fmt="text")
    second_count = len(logging.getLogger().handlers)
    assert first_count == second_count == 1


def test_configure_logging_text_mode_writes_message() -> None:
    configure_logging(level="DEBUG", fmt="text")
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(logging.Formatter("%(message)s"))
    log = logging.getLogger("greenhouse.test")
    log.addHandler(handler)
    try:
        log.warning("text-mode-check")
    finally:
        log.removeHandler(handler)
    assert "text-mode-check" in buffer.getvalue()
