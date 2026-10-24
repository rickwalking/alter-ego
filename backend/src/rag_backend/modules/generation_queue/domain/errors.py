"""Failures a generation job can end with, and their classification.

Transient failures retry with backoff; permanent ones dead-letter at once. A
failure nobody classified is taken as transient: the attempt budgets still stop
it. ``MemoryError`` is permanent: retrying an out-of-memory phase in the same
container only repeats it.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum

from rag_backend.modules.generation_queue.constants import (
    ERROR_PERMANENT,
    ERROR_TRANSIENT,
)


class FailureClass(StrEnum):
    """Retry or park."""

    TRANSIENT = ERROR_TRANSIENT
    PERMANENT = ERROR_PERMANENT


class DriveLockBusyError(Exception):
    """Another driver holds the project."""


class DriveLockLostError(Exception):
    """The lock connection died mid-drive: ownership is gone, stop driving."""


class BudgetExhaustedError(Exception):
    """A phase or the run used up its attempts."""

    def __init__(self, error_code: str) -> None:
        super().__init__(error_code)
        self.error_code = error_code


class PermanentGenerationError(Exception):
    """A failure no retry can fix (bad payload, unknown kind, missing project)."""

    def __init__(self, error_code: str, detail: str = "") -> None:
        super().__init__(detail or error_code)
        self.error_code = error_code


class DeadLetteredError(Exception):
    """Raised to PgQueuer after mirroring: the job is held as ``failed``."""


ProviderClassifier = Callable[[BaseException], bool]

_PERMANENT_TYPES: tuple[type[BaseException], ...] = (
    PermanentGenerationError,
    MemoryError,
    ValueError,
    LookupError,
    TypeError,
)
_TRANSIENT_TYPES: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError)


def classify(exc: BaseException, is_provider_error: ProviderClassifier) -> FailureClass:
    """Transient for timeouts, dropped connections and provider outages."""
    if isinstance(exc, _TRANSIENT_TYPES) or is_provider_error(exc):
        return FailureClass.TRANSIENT
    if isinstance(exc, _PERMANENT_TYPES):
        return FailureClass.PERMANENT
    return FailureClass.TRANSIENT


__all__ = [
    "BudgetExhaustedError",
    "DeadLetteredError",
    "DriveLockBusyError",
    "DriveLockLostError",
    "FailureClass",
    "PermanentGenerationError",
    "ProviderClassifier",
    "classify",
]
