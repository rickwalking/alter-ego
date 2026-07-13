"""Typed carousel conflict domain model (AE-0316)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rag_backend.domain.constants.carousel_conflicts import CONFLICT_MESSAGES


@dataclass(frozen=True)
class CarouselConflict:
    """A machine-readable 409 conflict on a carousel mutation or resume."""

    code: str
    message: str
    run_started_at: datetime | None = None
    phase: str | None = None

    @classmethod
    def for_code(
        cls,
        code: str,
        *,
        run_started_at: datetime | None = None,
        phase: str | None = None,
    ) -> CarouselConflict:
        """Build a conflict with the canonical message for ``code``."""
        return cls(
            code=code,
            message=CONFLICT_MESSAGES.get(code, code),
            run_started_at=run_started_at,
            phase=phase,
        )


class CarouselConflictError(Exception):
    """Raised by carousel services/routes instead of a bare 409."""

    def __init__(self, conflict: CarouselConflict) -> None:
        super().__init__(conflict.code)
        self.conflict = conflict


__all__ = ["CarouselConflict", "CarouselConflictError"]
