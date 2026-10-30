"""Legal boost status pairs. The store performs the compare-and-set."""

from __future__ import annotations

from rag_backend.modules.autopilot.boost_constants import (
    STATUS_ACTIVE,
    STATUS_APPROVED,
    STATUS_COMPLETED,
    STATUS_EXPIRED,
    STATUS_FAILED,
    STATUS_LAUNCHING,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_STOPPED,
)
from rag_backend.modules.autopilot.domain.boost import IllegalBoostTransitionError

_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        (STATUS_PENDING, STATUS_APPROVED),
        (STATUS_PENDING, STATUS_REJECTED),
        (STATUS_PENDING, STATUS_EXPIRED),
        (STATUS_PENDING, STATUS_FAILED),
        (STATUS_APPROVED, STATUS_LAUNCHING),
        (STATUS_APPROVED, STATUS_FAILED),
        (STATUS_LAUNCHING, STATUS_ACTIVE),
        (STATUS_LAUNCHING, STATUS_FAILED),
        (STATUS_ACTIVE, STATUS_COMPLETED),
        (STATUS_ACTIVE, STATUS_FAILED),
        (STATUS_ACTIVE, STATUS_STOPPED),
    }
)


def assert_transition(expected: str, new: str) -> None:
    """Raise when the pair is not in the table."""
    if (expected, new) not in _PAIRS:
        raise IllegalBoostTransitionError(expected, new)


__all__ = ["assert_transition"]
