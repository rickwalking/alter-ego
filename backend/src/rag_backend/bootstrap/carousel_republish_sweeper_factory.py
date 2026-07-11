"""Composition-root factory for the AE-0314 republish sweeper.

Builds the server-guaranteed republish watchdog from Settings. The sweep min-age
reuses the stale-run reaper's overdue window so a marked-but-abandoned edit is
rebuilt within a few minutes without a new setting.
"""

from __future__ import annotations

from rag_backend.domain.constants.carousel_slide_edit import (
    REPUBLISH_SWEEP_MIN_AGE_SECONDS,
)
from rag_backend.domain.protocols.carousel_run import CarouselRepublishSweeper
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.database.carousel_republish_sweeper import (
    CarouselRepublishSweeperConfig,
    CarouselRepublishSweeperRepository,
)


def build_republish_sweeper(settings: Settings) -> CarouselRepublishSweeper:
    """Assemble the republish sweeper from Settings (default min-age constant)."""
    min_age = getattr(
        settings,
        "carousel_republish_sweep_min_age_seconds",
        REPUBLISH_SWEEP_MIN_AGE_SECONDS,
    )
    return CarouselRepublishSweeperRepository(
        CarouselRepublishSweeperConfig(min_age_seconds=int(min_age))
    )


__all__ = ["build_republish_sweeper"]
