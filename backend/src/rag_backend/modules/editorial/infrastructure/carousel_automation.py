"""In-process carousel automation seam for other modules (QA r1).

The autopilot module drives the editorial workflow without HTTP. Everything
it needs from the legacy carousel service, repository, and ORM lives here so
it imports only the editorial facade. This is infrastructure: the editorial
application/domain layers stay free of the carousel ORM.

The carousel service, repository and ORM are imported lazily because the editorial
facade is loaded while the ORM registry is still initialising.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, TypeAlias, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.editorial_workflow_types import (
    EditorialWorkflowStartInput,
    ResumeWorkflowInput,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    PresentationPolicyError,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.content_mode import is_pov_family
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.modules.editorial.domain.models import CarouselProject, CarouselSlide
from rag_backend.modules.editorial.domain.ports import CarouselRepository
from rag_backend.modules.editorial.infrastructure.carousel_cover import (
    stage_slide_cover,
)
from rag_backend.modules.editorial.infrastructure.pov_inputs import PovInputsAcl

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.editorial_workflow_service import (
        EditorialWorkflowService,
    )
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

EditorialWorkflowEngine: TypeAlias = "EditorialWorkflowService"
AutomationResumeInput: TypeAlias = ResumeWorkflowInput


@dataclass(frozen=True, kw_only=True)
class AutomationStart:
    """Inputs for an unattended workflow start (no reviewer is assigned).

    ``persona_id`` is the persona that voices and scores the carousel.
    """

    topic: str
    audience: str
    brief: str
    sources: tuple[Mapping[str, str], ...]
    user_id: str
    persona_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class AutomationResume:
    """One approve or revise applied in-process on the caller's session."""

    project_id: str
    action: str
    reviewer_id: str
    feedback: str
    structured_feedback: Mapping[str, object] | None
    session: AsyncSession


@dataclass(frozen=True, kw_only=True)
class RunHeartbeat:
    """Phase status and the last run heartbeat of one carousel.

    ``updated_at`` is when the row last changed, used to time a parked workflow.
    """

    phase_status: str
    heartbeat_at: datetime | None
    updated_at: datetime | None = None


@dataclass(frozen=True, kw_only=True)
class CarouselReviewRow:
    """Fields a review message quotes. ``output_dir`` holds the slide files.

    The review line quotes ``audience``, ``niche`` and ``image_style``: who the
    carousel is for and its preset.
    """

    topic: str
    caption: str
    output_dir: str | None
    audience: str = ""
    niche: str = ""
    image_style: str = ""


def build_start_input(
    start: AutomationStart, persona: PersonaProfile | None = None
) -> EditorialWorkflowStartInput:
    """Engine start input with no reviewer, voiced by ``persona`` when given."""
    return EditorialWorkflowStartInput(
        topic=start.topic,
        audience=start.audience,
        brief=start.brief,
        sources=[dict(source) for source in start.sources],
        persona=persona,
        user_id=start.user_id,
        reviewer_id=None,
    )


def build_resume_input(resume: AutomationResume) -> ResumeWorkflowInput:
    """Engine resume input bound to the caller's session."""
    structured = resume.structured_feedback
    return ResumeWorkflowInput(
        project_id=resume.project_id,
        action=resume.action,
        reviewer_id=resume.reviewer_id,
        feedback=resume.feedback or None,
        db=resume.session,
        structured_feedback=dict(structured) if structured is not None else None,
    )


def is_provider_outage(exc: BaseException) -> bool:
    """True for a provider 429/503 the caller should retry later."""
    from rag_backend.application.services.carousel.provider_errors import (
        classify_provider_error,
    )

    return classify_provider_error(exc) is not None


def content_approve_blocker(state: Mapping[str, object]) -> str | None:
    """The engine's own content-approve check. None when approve would pass.

    Runs the exact validators ``resume`` runs, so a caller never approves a
    gate the engine then rejects. The error code is returned, not raised.
    """
    from rag_backend.application.services.carousel import (
        editorial_workflow_service_helpers as engine_checks,
    )

    prior = cast(CarouselWorkflowState, dict(state))
    try:
        engine_checks.validate_content_approve_persona_score(prior)
        engine_checks.validate_content_approve_presentation(prior)
    except (ValueError, TypeError) as exc:
        return str(exc) or type(exc).__name__
    return None


def slides_in_config(slides_config: str) -> int:
    """Slide count encoded in a ``slides_config`` string."""
    from rag_backend.application.services.carousel.types import (
        slide_count_from_config,
    )

    return slide_count_from_config(slides_config)


def expected_slide_total(project: CarouselProject) -> int:
    """Slides the editorial pipeline builds for ``project``.

    The outline agent sizes the carousel from the presentation contract's
    ``slide_count``, not from ``slides_config``, so the contract is the
    authority. A ranged contract (POV, Radar IA v4) is sized to the
    project's own slide count. The config is only a fallback when the contract
    is unreadable.
    """
    from rag_backend.application.services.carousel.project_policy import (
        project_policy,
    )

    try:
        return project_policy(project).slide_count
    except PresentationPolicyError:
        return slides_in_config(project.slides_config)


def hero_image_total(
    slides: Sequence[CarouselSlide], project: CarouselProject | None = None
) -> int:
    """Hero images the image phase generates for ``slides``.

    The image phase only illustrates the slide types in ``IMAGE_SLIDE_TYPES``
    that carry an image prompt (``filter_image_slides``). The CTA slide uses
    the owner avatar instead, so a 7-slide carousel has 6 hero images.
    A role contract counts only its ``image_required`` slides (POV:
    the point slides), the same rule the image phase applies.
    """
    from rag_backend.application.services.carousel.image_artwork import (
        artwork_slide_numbers,
    )
    from rag_backend.application.services.carousel.nodes.images import (
        filter_image_slides,
    )
    from rag_backend.application.services.carousel.types import unpack_extras

    artwork = artwork_slide_numbers(project) if project is not None else None
    data = [unpack_extras(slide) for slide in slides]
    return len(filter_image_slides(data, artwork))


class CarouselAutomationAcl:
    """Session-scoped carousel reads and the unattended project insert."""

    def __init__(self, session: AsyncSession) -> None:
        from rag_backend.infrastructure.database.carousel_repository import (
            PostgresCarouselRepository,
        )

        self._session = session
        self._repo = PostgresCarouselRepository(session)

    @property
    def repository(self) -> CarouselRepository:
        """The carousel repository port, for the publishing release ACL."""
        return self._repo

    async def create_project(self, project: CarouselProject) -> str:
        """Insert the project, stage its slide-1 photo, and return its id.

        A chosen GrokBot cover is staged too; a cover whose file is
        gone is dropped (slide 1 falls back to the default) rather than left
        to fail the render.
        """
        created = await self._repo.create_project(project)
        await PovInputsAcl(self._session).stage_hook_photo(created)
        if created.slide_cover is not None and not await stage_slide_cover(
            self._session, created
        ):
            created.slide_cover = None
            await self._repo.update_project(created)
        return str(created.id)

    async def start_input(self, start: AutomationStart) -> EditorialWorkflowStartInput:
        """The engine start input with the start's persona loaded (PR #106)."""
        persona = await PovInputsAcl(self._session).load_persona(start.persona_id)
        return build_start_input(start, persona)

    async def is_pov(self, project_id: str) -> bool:
        """True for a POV-family carousel (voice must be scored)."""
        project = await self.load_project(project_id)
        return project is not None and is_pov_family(project.content_mode)

    async def load_project(self, project_id: str) -> CarouselProject | None:
        """The carousel entity, or None when the id is unknown."""
        return await self._repo.get_project_by_id(UUID(project_id))

    async def slide_total(self, project_id: str) -> int:
        """Slides the pipeline builds for the project. Zero when it does not exist."""
        project = await self.load_project(project_id)
        if project is None:
            return 0
        return expected_slide_total(project)

    async def hero_image_total(self, project_id: str) -> int:
        """Hero images the image phase builds for the persisted slides.

        Zero when the project or its slides do not exist (the gate then revises).
        """
        project = await self.load_project(project_id)
        if project is None:
            return 0
        return hero_image_total(
            await self._repo.get_slides_by_project(project.id), project
        )

    async def heartbeat(self, project_id: str) -> RunHeartbeat | None:
        """Phase status and run heartbeat, or None when the row is missing."""
        row = await self._session.get(_carousel_model(), project_id)
        if row is None:
            return None
        return RunHeartbeat(
            phase_status=str(row.phase_status),
            heartbeat_at=row.run_heartbeat_at,
            updated_at=cast(datetime | None, row.updated_at),
        )

    async def review_row(self, project_id: str) -> CarouselReviewRow | None:
        """Title, caption, and output folder, or None when the row is missing."""
        row = await self._session.get(_carousel_model(), project_id)
        if row is None:
            return None
        return CarouselReviewRow(
            topic=_text(row.topic),
            caption=_text(row.caption),
            output_dir=cast(str | None, row.output_dir),
            audience=_text(row.audience),
            niche=_text(row.niche),
            image_style=_text(row.image_style),
        )

    async def topics_since(self, since: datetime) -> tuple[str, ...]:
        """Non-blank carousel topics created at or after ``since``."""
        model = _carousel_model()
        result = await self._session.execute(
            select(model.topic).where(model.created_at >= since)
        )
        return tuple(value for value in result.scalars().all() if value != "")


def _carousel_model() -> type[CarouselProjectModel]:
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    return CarouselProjectModel


def _text(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""


__all__ = [
    "AutomationResume",
    "AutomationStart",
    "CarouselAutomationAcl",
    "CarouselReviewRow",
    "EditorialWorkflowEngine",
    "RunHeartbeat",
    "build_resume_input",
    "build_start_input",
    "content_approve_blocker",
    "expected_slide_total",
    "hero_image_total",
    "is_provider_outage",
    "slides_in_config",
]
