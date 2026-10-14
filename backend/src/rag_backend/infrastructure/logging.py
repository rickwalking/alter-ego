"""Structured logging configuration using structlog."""

import logging
import re
import sys
from collections.abc import MutableMapping
from typing import cast, override

import structlog

from rag_backend.domain.constants.log_redaction import (
    GRAPH_QUERY_CREDENTIAL_PATTERN,
    GRAPH_QUERY_CREDENTIAL_REPLACEMENT,
    NOISY_HTTP_LOGGERS,
    TELEGRAM_BOT_PATH_PATTERN,
    TELEGRAM_BOT_PATH_REPLACEMENT,
)

_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(TELEGRAM_BOT_PATH_PATTERN), TELEGRAM_BOT_PATH_REPLACEMENT),
    (re.compile(GRAPH_QUERY_CREDENTIAL_PATTERN), GRAPH_QUERY_CREDENTIAL_REPLACEMENT),
)


def get_logger() -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return cast(structlog.BoundLogger, structlog.get_logger())


def redact_secrets(text: str) -> str:
    """Replace Telegram bot tokens and ``access_token`` query values."""
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


class SecretRedactingFilter(logging.Filter):
    """Stdlib filter that redacts the fully formatted message of a record."""

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        """Rewrite ``msg`` in place; never drops a record."""
        message = record.getMessage()
        redacted = redact_secrets(message)
        if redacted != message:
            record.msg = redacted
            record.args = None
        return True


def redact_event_dict(
    logger: object,
    method_name: str,
    event_dict: MutableMapping[str, object],
) -> MutableMapping[str, object]:
    """structlog processor: redact every string value before rendering."""
    del logger, method_name
    for key, value in event_dict.items():
        if isinstance(value, str):
            event_dict[key] = redact_secrets(value)
    return event_dict


def setup_logging(*, debug: bool = False) -> None:
    """Configure structured logging for the application.

    Args:
        debug: If True, use human-readable dev output. If False, use JSON for production.
    """
    log_level = logging.DEBUG if debug else logging.INFO

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if not debug
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            redact_event_dict,
            renderer,
        ],
        wrapper_class=structlog.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    _harden_stdlib_logging()


def _harden_stdlib_logging() -> None:
    """Pin noisy HTTP loggers to WARNING and redact every stdlib handler."""
    redactor = SecretRedactingFilter()
    for name in NOISY_HTTP_LOGGERS:
        http_logger = logging.getLogger(name)
        http_logger.setLevel(logging.WARNING)
        _add_once(http_logger, redactor)
    for handler in logging.getLogger().handlers:
        _add_once(handler, redactor)


def _add_once(target: logging.Filterer, redactor: SecretRedactingFilter) -> None:
    if any(isinstance(item, SecretRedactingFilter) for item in target.filters):
        return
    target.addFilter(redactor)
