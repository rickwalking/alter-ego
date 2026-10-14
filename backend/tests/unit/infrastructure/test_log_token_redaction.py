"""Token redaction and httpx log pinning (QA r1 S-W2).

Gherkin: tests/features/log_token_redaction.feature
"""

from __future__ import annotations

import io
import logging
from collections.abc import Iterator

import pytest
import structlog

from rag_backend.infrastructure.logging import (
    SecretRedactingFilter,
    redact_secrets,
    setup_logging,
)

_BOT_URL = "https://api.telegram.org/bot123456:AAH-secret_tok/sendMessage"
_GRAPH_URL = "https://graph.instagram.com/me?fields=id&access_token=IGQ.secret-val&x=1"


@pytest.fixture
def stdout(monkeypatch: pytest.MonkeyPatch) -> Iterator[io.StringIO]:
    """Configure logging onto a buffer, then restore the root logger."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    for handler in saved_handlers:
        root.removeHandler(handler)
    buffer = io.StringIO()
    monkeypatch.setattr("sys.stdout", buffer)
    setup_logging(debug=False)
    yield buffer
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for handler in saved_handlers:
        root.addHandler(handler)
    root.setLevel(saved_level)
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.NOTSET)
        logging.getLogger(name).filters.clear()
    structlog.reset_defaults()


# Scenario: httpx request lines are not logged at INFO
def test_httpx_info_is_suppressed(stdout: io.StringIO) -> None:
    logging.getLogger("httpx").info('HTTP Request: POST %s "HTTP/1.1 200 OK"', _BOT_URL)
    logging.getLogger("httpcore.http11").info("send_request_headers %s", _BOT_URL)
    assert stdout.getvalue() == ""
    assert logging.getLogger("httpx").getEffectiveLevel() == logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() == logging.WARNING


# Scenario: A warning with a bot URL and an access token is redacted
def test_stdlib_warning_is_redacted(stdout: io.StringIO) -> None:
    logging.getLogger("httpx").warning("retry %s then %s", _BOT_URL, _GRAPH_URL)
    logging.getLogger("some.other").warning("failed %s", _GRAPH_URL)
    rendered = stdout.getvalue()
    assert "/bot<redacted>/sendMessage" in rendered
    assert "access_token=<redacted>&x=1" in rendered
    assert "AAH-secret_tok" not in rendered
    assert "IGQ.secret-val" not in rendered


# Scenario: A structlog event with a secret URL is redacted
def test_structlog_event_is_redacted(stdout: io.StringIO) -> None:
    structlog.configure(logger_factory=structlog.PrintLoggerFactory(file=stdout))
    structlog.get_logger().warning("graph_call", url=_GRAPH_URL, bot=_BOT_URL)
    rendered = stdout.getvalue()
    assert "access_token=<redacted>" in rendered
    assert "/bot<redacted>" in rendered
    assert "IGQ.secret-val" not in rendered
    assert "AAH-secret_tok" not in rendered


def test_redaction_is_idempotent_and_leaves_plain_text() -> None:
    once = redact_secrets(_BOT_URL)
    assert redact_secrets(once) == once
    assert redact_secrets("plain message") == "plain message"


def test_filter_keeps_records_without_secrets() -> None:
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "hi %s", ("you",), None)
    assert SecretRedactingFilter().filter(record) is True
    assert record.getMessage() == "hi you"


def test_setup_logging_twice_adds_one_filter(stdout: io.StringIO) -> None:
    setup_logging(debug=False)
    filters = logging.getLogger("httpx").filters
    assert sum(isinstance(item, SecretRedactingFilter) for item in filters) == 1
