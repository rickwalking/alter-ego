"""Rate-limit-aware retry for provider image generation (AE-0208).

The OpenAI org image cap is 5/min; a multi-slide carousel that fires every
slide at once 429s. Two complementary controls live here:

- a configurable ``asyncio.Semaphore`` factory so the batch never exceeds the
  documented per-minute provider cap;
- :func:`generate_with_retry_after`, which retries a single generation on HTTP
  429 and waits **at least** the provider-stated ``retry-after`` (the OpenAI
  SDK's internal ``max_retries`` back off only ~0.4-0.9s, far below the 12s the
  provider asks for), falling back to bounded exponential backoff otherwise.

This module is framework- and infrastructure-free (pure application logic):
callers observe retries via the optional ``on_retry`` callback so logging stays
in the (already infrastructure-aware) image node.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from rag_backend.application.services.carousel.image_generation_constants import (
    DEFAULT_RETRY_BACKOFF_SECONDS,
    HTTP_STATUS_TOO_MANY_REQUESTS,
    MAX_RETRY_BACKOFF_SECONDS,
    MIN_IMAGE_ATTEMPTS,
    MIN_IMAGE_CONCURRENCY,
    RETRY_AFTER_HEADER,
    RETRY_AFTER_MARGIN_SECONDS,
)

SleepFn = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class RetryEvent:
    """A single rate-limit retry, surfaced to the caller for observability."""

    attempt: int
    max_attempts: int
    wait_seconds: float
    retry_after: float | None


@dataclass(frozen=True)
class RetryOptions:
    """Grouped controls for :func:`generate_with_retry_after`.

    ``sleep`` is resolved at call time (default ``asyncio.sleep``) so tests can
    substitute a no-wait stub via the module-level ``asyncio.sleep``.
    """

    max_attempts: int
    on_retry: Callable[[RetryEvent], None] | None = None
    sleep: SleepFn | None = None


def build_image_semaphore(concurrency: int) -> asyncio.Semaphore:
    """Build a concurrency gate clamped to at least one in-flight request."""
    return asyncio.Semaphore(max(concurrency, MIN_IMAGE_CONCURRENCY))


def _status_code(exc: BaseException) -> int | None:
    """Best-effort HTTP status extraction from a provider error."""
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def _is_rate_limited(exc: BaseException) -> bool:
    return _status_code(exc) == HTTP_STATUS_TOO_MANY_REQUESTS


def _retry_after_seconds(exc: BaseException) -> float | None:
    """Read and parse the provider's ``retry-after`` header, if present."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    raw = headers.get(RETRY_AFTER_HEADER)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _wait_seconds(exc: BaseException, attempt: int) -> float:
    """Resolve the wait before the next attempt.

    Honor the provider-stated ``retry-after`` (plus a small margin) when given;
    otherwise fall back to bounded exponential backoff.
    """
    stated = _retry_after_seconds(exc)
    if stated is not None:
        return stated + RETRY_AFTER_MARGIN_SECONDS
    backoff = DEFAULT_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
    return min(backoff, MAX_RETRY_BACKOFF_SECONDS)


async def generate_with_retry_after(
    generate: Callable[[], Awaitable[None]],
    options: RetryOptions,
) -> None:
    """Run ``generate``; on a 429 wait >= the stated retry-after, then retry.

    Non-429 errors and the final 429 are re-raised unchanged so the caller's
    existing failure handling (logging + failure record) is preserved.
    """
    sleep_fn: SleepFn = options.sleep if options.sleep is not None else asyncio.sleep
    attempts = max(options.max_attempts, MIN_IMAGE_ATTEMPTS)
    attempt = 1
    while True:
        try:
            await generate()
        except Exception as exc:
            if attempt >= attempts or not _is_rate_limited(exc):
                raise
            wait = _wait_seconds(exc, attempt)
            if options.on_retry is not None:
                options.on_retry(
                    RetryEvent(
                        attempt=attempt,
                        max_attempts=attempts,
                        wait_seconds=wait,
                        retry_after=_retry_after_seconds(exc),
                    )
                )
            await sleep_fn(wait)
            attempt += 1
        else:
            return


__all__ = [
    "RetryEvent",
    "RetryOptions",
    "build_image_semaphore",
    "generate_with_retry_after",
]
