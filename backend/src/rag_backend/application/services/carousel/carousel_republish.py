"""Idempotent republish of a completed carousel's artifacts (AE-0313).

Re-renders slides/PDFs from the persisted slide data, health-checks the fresh
pre-promotion outputs, then builds and activates a new content-addressed
artifact version — all under the shared per-project advisory lock so a republish
can never interleave with AE-0311's repair, AE-0314's slide edit, or another
republish.

Lock scope (pinned by AE-0313 cold-critic r3): the session-scoped advisory lock
is acquired ONCE for the whole pipeline — the digest/manifest computation, the
``activate_build`` CAS, and the ``write_current_index`` all sit inside a single
critical section. The lock lives on its own connection (AE-0316) so it spans the
finalize pipeline's transactions.

The non-blocking acquire raises AE-0316's ``mutation_in_progress`` conflict when
another holder has the lock; the republish path re-labels that as the more
specific ``build_in_progress`` (an artifact build/republish is already running),
while any conflict raised INSIDE the critical section propagates unchanged.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from rag_backend.application.services.carousel.editorial_finalize import (
    CarouselFinalizeResult,
    finalize_carousel_after_images_approval,
)
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_BUILD_IN_PROGRESS,
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
)
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.modules.editorial.public import carousel_project_lock

logger = structlog.get_logger()

_ERR_ENGINE_UNAVAILABLE = "carousel republish requires an async engine bind"


def engine_from_session(db: AsyncSession) -> AsyncEngine:
    """Return the request session's bound AsyncEngine for the advisory lock.

    The lock needs a dedicated connection off the engine (not the request
    session) so it survives the finalize pipeline's commits.
    """
    bind = db.bind
    if not isinstance(bind, AsyncEngine):
        raise TypeError(_ERR_ENGINE_UNAVAILABLE)
    return bind


def _build_in_progress_error() -> CarouselConflictError:
    return CarouselConflictError(
        CarouselConflict.for_code(CONFLICT_CODE_BUILD_IN_PROGRESS)
    )


@asynccontextmanager
async def republish_build_lock(
    engine: AsyncEngine,
    project_id: str,
) -> AsyncIterator[None]:
    """Hold the shared per-project lock, surfaced as ``build_in_progress``."""
    try:
        async with carousel_project_lock(engine, project_id, blocking=False):
            yield
    except CarouselConflictError as exc:
        if exc.conflict.code == CONFLICT_CODE_MUTATION_IN_PROGRESS:
            raise _build_in_progress_error() from exc
        raise


async def republish_completed_carousel(
    db: AsyncSession,
    project_id: str,
) -> CarouselFinalizeResult:
    """Re-render + rebuild + activate the artifact version under the build lock."""
    engine = engine_from_session(db)
    async with republish_build_lock(engine, project_id):
        result = await finalize_carousel_after_images_approval(db, project_id)
    logger.info(
        "carousel_republish_finished",
        project_id=project_id,
        completed=result.completed,
    )
    return result


__all__ = [
    "engine_from_session",
    "republish_build_lock",
    "republish_completed_carousel",
]
