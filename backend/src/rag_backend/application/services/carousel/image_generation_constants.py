"""Constants for rate-limit-aware, partial-commit image generation.

AE-0208: concurrency cap + ``retry-after``-honoring backoff for provider 429s.
AE-0209: per-slide partial-commit + idempotent re-entry signalling.
"""

from __future__ import annotations

# Floor for the configurable provider-concurrency cap. A value below 1 would
# deadlock the semaphore, so we clamp up to a single in-flight request.
MIN_IMAGE_CONCURRENCY = 1

# Floor for the configurable retry-attempt budget (at least one attempt).
MIN_IMAGE_ATTEMPTS = 1

# Application-layer fallbacks used when the caller does not inject explicit
# values (settings-backed values are passed in from the infrastructure-aware
# editorial pipeline; these keep direct callers / unit tests safe and capped at
# the documented OpenAI org image cap of 5/min).
DEFAULT_IMAGE_CONCURRENCY = 5
DEFAULT_IMAGE_MAX_ATTEMPTS = 5

# HTTP 429 — Too Many Requests (provider rate limit).
HTTP_STATUS_TOO_MANY_REQUESTS = 429

# Response header carrying the provider's requested wait before retrying.
RETRY_AFTER_HEADER = "retry-after"

# Backoff bounds used when the provider does NOT supply a ``retry-after``
# (or supplies an unparseable value): exponential 2**n seconds, clamped.
DEFAULT_RETRY_BACKOFF_SECONDS = 1.0
MAX_RETRY_BACKOFF_SECONDS = 60.0

# Small safety margin added on top of the provider-stated wait so we resume
# strictly after the window the provider asked us to wait, never on its edge.
RETRY_AFTER_MARGIN_SECONDS = 0.5

# Structured-log events.
LOG_IMAGE_RATE_LIMITED = "carousel_image_rate_limited"
LOG_IMAGE_BATCH_PARTIAL_FAILURE = "carousel_image_batch_partial_failure"

# Aggregate error raised after a batch when one or more slides failed but the
# successful slides have already been committed (AE-0209 partial commit).
ERR_IMAGE_BATCH_PARTIAL = (
    "Image generation completed with {failed} of {total} slide(s) failed; "
    "successful slides were persisted and can be regenerated on re-run."
)

__all__ = [
    "DEFAULT_IMAGE_CONCURRENCY",
    "DEFAULT_IMAGE_MAX_ATTEMPTS",
    "DEFAULT_RETRY_BACKOFF_SECONDS",
    "ERR_IMAGE_BATCH_PARTIAL",
    "HTTP_STATUS_TOO_MANY_REQUESTS",
    "LOG_IMAGE_BATCH_PARTIAL_FAILURE",
    "LOG_IMAGE_RATE_LIMITED",
    "MAX_RETRY_BACKOFF_SECONDS",
    "MIN_IMAGE_ATTEMPTS",
    "MIN_IMAGE_CONCURRENCY",
    "RETRY_AFTER_HEADER",
    "RETRY_AFTER_MARGIN_SECONDS",
]
