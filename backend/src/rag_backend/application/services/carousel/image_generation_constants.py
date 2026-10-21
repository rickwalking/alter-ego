"""Constants for rate-limit-aware, partial-commit image generation.

Concurrency cap + ``retry-after``-honoring backoff for provider 429s, and
per-slide partial-commit + idempotent re-entry signalling.

MIN_IMAGE_CONCURRENCY clamps the configurable cap to one in-flight request, since a
value below 1 would deadlock the semaphore. The DEFAULT_IMAGE_* values are fallbacks for
callers that inject nothing (settings-backed values come from the editorial pipeline),
capped at the OpenAI org image limit of 5 per minute. Without a parseable retry-after
header the backoff is exponential (2**n seconds) within the DEFAULT/MAX bounds, and
RETRY_AFTER_MARGIN_SECONDS is added so a retry resumes strictly after the provider's
window. ERR_IMAGE_BATCH_PARTIAL is raised after a batch where some slides failed but the
successful ones are already committed.
"""

from __future__ import annotations

MIN_IMAGE_CONCURRENCY = 1

MIN_IMAGE_ATTEMPTS = 1

DEFAULT_IMAGE_CONCURRENCY = 5
DEFAULT_IMAGE_MAX_ATTEMPTS = 5

HTTP_STATUS_TOO_MANY_REQUESTS = 429

RETRY_AFTER_HEADER = "retry-after"

DEFAULT_RETRY_BACKOFF_SECONDS = 1.0
MAX_RETRY_BACKOFF_SECONDS = 60.0

RETRY_AFTER_MARGIN_SECONDS = 0.5

LOG_IMAGE_RATE_LIMITED = "carousel_image_rate_limited"
LOG_IMAGE_BATCH_PARTIAL_FAILURE = "carousel_image_batch_partial_failure"

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
