"""Structured logging configuration using structlog."""

import logging
import sys

import structlog


def get_logger():
    """Get a structured logger instance."""
    return structlog.get_logger()


def setup_logging(*, debug: bool = False) -> None:
    """Configure structured logging for the application.

    Args:
        debug: If True, use human-readable dev output. If False, use JSON for production.
    """
    log_level = logging.DEBUG if debug else logging.INFO

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if not debug else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[*shared_processors, structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
