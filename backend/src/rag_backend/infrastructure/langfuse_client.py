"""LangFuse client initialization and management."""

from collections.abc import Callable
from threading import Event, Lock, Thread

import structlog
from langfuse import Langfuse

from rag_backend.infrastructure.config.settings import get_settings

LANGFUSE_CLIENT: Langfuse | None = None

logger = structlog.get_logger(__name__)

_FLUSH_EVENT = Event()
_FLUSH_LOCK = Lock()
_FLUSH_PENDING: Callable[[], None] | None = None
_FLUSH_THREAD: Thread | None = None


def init_langfuse(
    public_key: str | None, secret_key: str, host: str
) -> Langfuse | None:
    """Initialize LangFuse tracing.

    Returns None if not configured.
    """
    global LANGFUSE_CLIENT
    if not public_key and not secret_key:
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


def _flush_worker() -> None:
    """Flush the latest requested client without blocking the caller."""
    global _FLUSH_PENDING
    while True:
        _FLUSH_EVENT.wait()
        with _FLUSH_LOCK:
            flush = _FLUSH_PENDING
            _FLUSH_PENDING = None
            _FLUSH_EVENT.clear()
        if flush is None:
            continue
        try:
            flush()
        except Exception:
            logger.warning("langfuse_background_flush_failed")


def schedule_flush(flush: Callable[[], None]) -> None:
    """Request a coalesced background flush; callers never wait on the exporter."""
    global _FLUSH_PENDING, _FLUSH_THREAD
    with _FLUSH_LOCK:
        _FLUSH_PENDING = flush
        if _FLUSH_THREAD is None or not _FLUSH_THREAD.is_alive():
            _FLUSH_THREAD = Thread(
                target=_flush_worker,
                name="langfuse-flush",
                daemon=True,
            )
            _FLUSH_THREAD.start()
    _FLUSH_EVENT.set()


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
