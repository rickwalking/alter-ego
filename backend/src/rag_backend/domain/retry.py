"""Retry utilities for external API calls using tenacity."""

import httpx
from tenacity import (
    AsyncRetrying,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from rag_backend.domain.constants.retry import (
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_MIN_WAIT_SECONDS,
)

_RETRYABLE_HTTP_CODES: frozenset[int] = frozenset(
    {
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    }
)


def _is_retryable_http(exc: BaseException) -> bool:
    """Check if an HTTP error has a retryable status code."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_HTTP_CODES
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.ConnectError):
        return True
    if isinstance(exc, httpx.RemoteProtocolError):
        return True
    return False


def _is_retryable_api_error(exc: BaseException) -> bool:
    """Check if an API or network error should be retried."""
    if _is_retryable_http(exc):
        return True
    error_msg = str(exc).lower()
    retryable_patterns = (
        "rate limit",
        "timeout",
        "internal server error",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "too many requests",
        "connection",
        "temporarily",
        "retry",
        "server error",
        "try again",
    )
    return any(pattern in error_msg for pattern in retryable_patterns)


_RETRYABLE_EXCEPTIONS = (httpx.HTTPError, ConnectionError, TimeoutError, OSError)


DEFAULT_RETRY_CONFIG = {
    "stop": stop_after_attempt(DEFAULT_MAX_ATTEMPTS),
    "wait": wait_exponential(
        multiplier=DEFAULT_MIN_WAIT_SECONDS,
        min=DEFAULT_MIN_WAIT_SECONDS,
        max=DEFAULT_MAX_WAIT_SECONDS,
    ),
    "retry": retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
}


def retry_sync(
    attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: float = DEFAULT_MIN_WAIT_SECONDS,
    max_wait: float = DEFAULT_MAX_WAIT_SECONDS,
) -> Retrying:
    """Create a synchronous retry context manager."""
    return Retrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=min_wait, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        reraise=True,
    )


def retry_async(
    attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: float = DEFAULT_MIN_WAIT_SECONDS,
    max_wait: float = DEFAULT_MAX_WAIT_SECONDS,
) -> AsyncRetrying:
    """Create an async retry context manager."""
    return AsyncRetrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=min_wait, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        reraise=True,
    )
