"""LangFuse client initialization and management."""

from collections.abc import Callable
from threading import Semaphore, Thread

import structlog
from langfuse import Langfuse

from rag_backend.infrastructure.config.settings import get_settings

LANGFUSE_CLIENT: Langfuse | None = None

logger = structlog.get_logger(__name__)

_MAX_ACTIVE_FLUSHES = 8
_FLUSH_SLOTS = Semaphore(_MAX_ACTIVE_FLUSHES)


def init_langfuse(
    public_key: str | None, secret_key: str, host: str
) -> Langfuse | None:
    """Initialize LangFuse tracing.

    Tracing needs both keys: with either one missing it stays disabled and
    returns None, so a half-configured deploy never starts a client whose every
    export is rejected.
    """
    global LANGFUSE_CLIENT
    if not public_key or not secret_key:
        LANGFUSE_CLIENT = None
        return None
    try:
        LANGFUSE_CLIENT = Langfuse(
            public_key=public_key or "",
            secret_key=secret_key,
            base_url=host,
        )
        from rag_backend import monitoring_langfuse as root_monitoring

        root_monitoring.init_langfuse(
            public_key or "",
            secret_key,
            host,
        )
        return LANGFUSE_CLIENT
    except ImportError:
        LANGFUSE_CLIENT = None
        return None


def get_langfuse_client() -> Langfuse | None:
    """Get the LangFuse client.

    Returns:
        LangFuse client instance or None
    """
    global LANGFUSE_CLIENT
    if LANGFUSE_CLIENT is None:
        settings = get_settings()
        LANGFUSE_CLIENT = init_langfuse(
            settings.langfuse_public_key,
            (
                settings.langfuse_secret_key.get_secret_value()
                if settings.langfuse_secret_key
                else ""
            ),
            settings.langfuse_host,
        )
    return LANGFUSE_CLIENT


def _run_flush(flush: Callable[[], None]) -> None:
    """Run one flush, then release its bounded slot."""
    try:
        flush()
    except Exception:
        logger.warning("langfuse_background_flush_failed")
    finally:
        _FLUSH_SLOTS.release()


def schedule_flush(flush: Callable[[], None]) -> None:
    """Request a background flush; callers never wait on the exporter.

    Each request runs on a daemon thread, capped at
    ``_MAX_ACTIVE_FLUSHES``. When the exporter hangs, excess requests are
    dropped (tracing is best-effort) instead of blocking business work or
    growing an unbounded queue. A hung flush cannot starve later flushes.
    """
    if not _FLUSH_SLOTS.acquire(blocking=False):
        logger.warning("langfuse_background_flush_dropped")
        return
    try:
        Thread(
            target=_run_flush,
            args=(flush,),
            name="langfuse-flush",
            daemon=True,
        ).start()
    except Exception:
        _FLUSH_SLOTS.release()
        raise


def flush_langfuse() -> None:
    """Flush buffered observations without blocking the business path.

    Deliberately does not lazily initialize Langfuse: a runner shutdown must
    never create a client (and open a network connection) just to flush.
    """
    client = LANGFUSE_CLIENT
    if client is None:
        return
    try:
        schedule_flush(client.flush)
    except Exception:
        logger.warning("langfuse_background_flush_schedule_failed")


__all__ = [
    "flush_langfuse",
    "get_langfuse_client",
    "init_langfuse",
    "schedule_flush",
]
