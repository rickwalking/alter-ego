"""Constants for the carousel artifact republish flow.

Republish is only valid for a completed carousel. When the finalize pipeline fails on a
completed project, the project stays on its prior version and the error is surfaced to
the caller.
"""

ERR_REPUBLISH_NOT_COMPLETED = "carousel must be completed to republish"

ERR_REPUBLISH_FAILED = "carousel republish failed; the previous version is unchanged"

REPUBLISH_STATUS_REPUBLISHED = "republished"

__all__ = [
    "ERR_REPUBLISH_FAILED",
    "ERR_REPUBLISH_NOT_COMPLETED",
    "REPUBLISH_STATUS_REPUBLISHED",
]
