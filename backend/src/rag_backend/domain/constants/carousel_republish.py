"""Constants for the carousel artifact republish flow (AE-0313)."""

# Precondition failure: republish is only valid for a completed carousel.
ERR_REPUBLISH_NOT_COMPLETED = "carousel must be completed to republish"

# Generic republish failure detail when the finalize pipeline returned errors
# on an already-completed project (the project is preserved on its prior
# version; the error is surfaced to the caller).
ERR_REPUBLISH_FAILED = "carousel republish failed; the previous version is unchanged"

# Successful republish response status.
REPUBLISH_STATUS_REPUBLISHED = "republished"

__all__ = [
    "ERR_REPUBLISH_FAILED",
    "ERR_REPUBLISH_NOT_COMPLETED",
    "REPUBLISH_STATUS_REPUBLISHED",
]
