"""One automatic slide-1 cover generation for a fresh autopilot carousel.

The caller (the autopilot) decides consent; this helper runs the existing
request path unchanged: the owner's current library photos (role ``hook``, the
newest up to three) as references, the carousel topic as the direction, the
same caps and the same tracked background task. Every refusal of the manual
path applies here (not a POV carousel, a cap reached, a generation already
pending) and becomes a skip with the refusal's code as the reason. A carousel
that already has a generation row (any status) is skipped, so a re-driven or
retried run never enqueues a second job.

Once the run settles ``succeeded`` the cover becomes slide 1's cover, unless
a cover was already chosen or the owner chose one since the job was
scheduled (see ``carousel_cover_autoselect``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.cover_generation import (
    COVER_GENERATION_MAX_PHOTOS,
    COVER_GENERATION_PROMPT_MIN_LEN,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.modules.editorial.infrastructure.carousel_automation import (
    CarouselAutomationAcl,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_autoselect import (
    selecting_cover_task,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_generation import (
    CoverRunWiring,
    cover_generation_service,
    cover_run_wiring,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_pick import (
    EditorialCoverLibrary,
)

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.cover_generation import (
        CoverGenerationRun,
    )

REASON_AUTO_COVER_ALREADY_EXISTS = "already_exists"
REASON_AUTO_COVER_NO_PROJECT = "no_project"
REASON_AUTO_COVER_NO_PHOTOS = "no_photos"
REASON_AUTO_COVER_NO_DIRECTION = "no_direction"
REASON_AUTO_COVER_UNAVAILABLE = "bridge_unavailable"
REASON_AUTO_COVER_REFUSED = "refused"


@dataclass(frozen=True)
class AutoCoverOutcome:
    """Whether the job was recorded and scheduled, and why not."""

    scheduled: bool
    reason: str = ""
    generation_id: str = ""


def _skip(reason: str) -> AutoCoverOutcome:
    return AutoCoverOutcome(scheduled=False, reason=reason)


async def _selected_photos(session: AsyncSession, owner_id: str) -> tuple[UUID, ...]:
    """Up to three of the owner's library photos, newest first."""
    photos = await EditorialCoverLibrary(session).photos(owner_id)
    return tuple(asset.id for asset in photos[:COVER_GENERATION_MAX_PHOTOS])


async def schedule_autopilot_cover(
    session: AsyncSession, project_id: str
) -> AutoCoverOutcome:
    """Record one pending cover generation and schedule its background run."""
    from rag_backend.modules.editorial.infrastructure.cover_generations import (
        SqlCoverGenerationRepository,
    )

    project = await CarouselAutomationAcl(session).load_project(project_id)
    if project is None or not project.owner_id:
        return _skip(REASON_AUTO_COVER_NO_PROJECT)
    if await SqlCoverGenerationRepository(session).for_project(project_id):
        return _skip(REASON_AUTO_COVER_ALREADY_EXISTS)
    if len(project.topic.strip()) < COVER_GENERATION_PROMPT_MIN_LEN:
        return _skip(REASON_AUTO_COVER_NO_DIRECTION)
    selected = await _selected_photos(session, project.owner_id)
    if not selected:
        return _skip(REASON_AUTO_COVER_NO_PHOTOS)
    return await _start_cover(session, project, selected)


async def _start_cover(
    session: AsyncSession, project: CarouselProject, photos: tuple[UUID, ...]
) -> AutoCoverOutcome:
    """Start and schedule through the existing request path."""
    wiring = _wiring(len(photos))
    if wiring is None:
        return _skip(REASON_AUTO_COVER_UNAVAILABLE)
    run = await _record_generation(session, project, photos)
    if isinstance(run, str):
        return _skip(run)
    _schedule(wiring, run, project)
    return AutoCoverOutcome(scheduled=True, generation_id=str(run.generation.id))


async def _record_generation(
    session: AsyncSession, project: CarouselProject, photos: tuple[UUID, ...]
) -> CoverGenerationRun | str:
    """The pending generation, or the refusal as a skip reason."""
    from rag_backend.application.services.carousel.cover_generation import (
        CoverGenerationError,
        StartCoverGeneration,
    )

    try:
        return await cover_generation_service(session).start(
            StartCoverGeneration(
                project=project,
                user_id=project.owner_id or "",
                photo_ids=photos,
                prompt=project.topic.strip(),
                confirmed=True,
            )
        )
    except CoverGenerationError as exc:
        return f"{REASON_AUTO_COVER_REFUSED}:{exc.code}"


def _schedule(
    wiring: CoverRunWiring, run: CoverGenerationRun, project: CarouselProject
) -> None:
    """Hand the run, then the slide-1 selection, to the tracked background task."""
    from rag_backend.application.services.carousel.cover_generation_tasks import (
        schedule_cover_generation,
    )

    task = selecting_cover_task(wiring, run, project)
    schedule_cover_generation(task, str(run.generation.id))


def _wiring(photo_count: int) -> CoverRunWiring | None:
    """The bridge wiring; None when the image bridge is not configured."""
    from rag_backend.agents.cover_generation_prompts import cover_prompt_for
    from rag_backend.modules.image_bridge import ImageBridgeConfigError

    try:
        return cover_run_wiring(cover_prompt_for(photo_count))
    except ImageBridgeConfigError:
        return None


__all__ = [
    "REASON_AUTO_COVER_ALREADY_EXISTS",
    "REASON_AUTO_COVER_NO_DIRECTION",
    "REASON_AUTO_COVER_NO_PHOTOS",
    "REASON_AUTO_COVER_NO_PROJECT",
    "REASON_AUTO_COVER_REFUSED",
    "REASON_AUTO_COVER_UNAVAILABLE",
    "AutoCoverOutcome",
    "schedule_autopilot_cover",
]
