"""LangFuse client initialization and management."""

import asyncio
from collections.abc import Callable
from threading import Semaphore, Thread
from urllib.parse import urlsplit

import httpx
import structlog
from langfuse import Langfuse
from langfuse.api.core.request_options import RequestOptions

from rag_backend.infrastructure.config.settings import get_settings

LANGFUSE_CLIENT: Langfuse | None = None

logger = structlog.get_logger(__name__)

_MAX_ACTIVE_FLUSHES = 8
_FLUSH_SLOTS = Semaphore(_MAX_ACTIVE_FLUSHES)
_LANGFUSE_AUTH_TIMEOUT_SECONDS = 5
_AUTH_TASKS: set[asyncio.Task[None]] = set()
_REDACTED_HOST = "<redacted>"
_SAFE_HOST_SCHEMES = frozenset({"http", "https"})


class AuthCheckFailedError(Exception):
    """The Langfuse public projects response did not authenticate the client."""


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


def safe_langfuse_host(host: str) -> str:
    """Return only the HTTP(S) origin for credential-free diagnostics."""
    try:
        parsed = urlsplit(host)
        if parsed.scheme not in _SAFE_HOST_SCHEMES or not parsed.hostname:
            return _REDACTED_HOST
        hostname = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
        port = f":{parsed.port}" if parsed.port is not None else ""
        return f"{parsed.scheme}://{hostname}{port}"
    except ValueError:
        return _REDACTED_HOST


def _auth_failure_reason(error: Exception) -> str:
    status_code = getattr(error, "status_code", None)
    if isinstance(status_code, int):
        return str(status_code)
    return type(error).__name__


def _log_auth_exception(error: Exception, host: str) -> None:
    reason = _auth_failure_reason(error)
    if isinstance(error, (TimeoutError, httpx.RequestError, OSError)):
        logger.warning("langfuse_auth_unreachable", host=host, reason=reason)
        return
    logger.warning("langfuse_auth_failed", host=host, reason=reason)


def _check_projects(client: Langfuse) -> bool:
    request_options: RequestOptions = {
        "timeout_in_seconds": _LANGFUSE_AUTH_TIMEOUT_SECONDS,
        "max_retries": 0,
    }
    projects = client.api.projects.get(request_options=request_options)
    return bool(projects.data)


def _require_authenticated(*, authenticated: bool) -> None:
    if not authenticated:
        raise AuthCheckFailedError


async def _run_auth_check(client: Langfuse, host: str) -> None:
    try:
        authenticated = await asyncio.wait_for(
            asyncio.to_thread(_check_projects, client),
            timeout=_LANGFUSE_AUTH_TIMEOUT_SECONDS,
        )
        _require_authenticated(authenticated=authenticated)
    except Exception as error:
        _log_auth_exception(error, host)
        return
    logger.info("langfuse_auth_ok", host=host)


def schedule_langfuse_auth_check(client: Langfuse, host: str) -> asyncio.Task[None]:
    """Run one bounded credential check without blocking the caller."""
    task = asyncio.create_task(_run_auth_check(client, safe_langfuse_host(host)))
    _AUTH_TASKS.add(task)
    task.add_done_callback(_AUTH_TASKS.discard)
    return task


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
    "safe_langfuse_host",
    "schedule_flush",
    "schedule_langfuse_auth_check",
]
