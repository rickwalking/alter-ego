"""In-process carousel automation seam for other modules (AE-0348 QA r1).

The autopilot module drives the editorial workflow without HTTP. Everything
it needs from the legacy carousel service, repository, and ORM lives here so
it imports only the editorial facade. This is infrastructure: the editorial
application/domain layers stay free of the carousel ORM.
"""

from __future__ import annotations

from collections.abc import Mapping
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
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.modules.editorial.domain.models import CarouselProject
from rag_backend.modules.editorial.domain.ports import CarouselRepository

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.editorial_workflow_service import (
        EditorialWorkflowService,
    )
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

# The concrete workflow engine. Callers type their engine factory with it.
# The service, the repository and the ORM are imported lazily: the editorial
# facade is loaded while the ORM registry is still initialising.
EditorialWorkflowEngine: TypeAlias = "EditorialWorkflowService"
# The engine resume input ``build_resume_input`` returns (QA r2 R6).
AutomationResumeInput: TypeAlias = ResumeWorkflowInput


@dataclass(frozen=True, kw_only=True)
class AutomationStart:
    """Inputs for an unattended workflow start (no reviewer is assigned)."""

    topic: str
    audience: str
    brief: str
    sources: tuple[Mapping[str, str], ...]
    user_id: str


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
    """Phase status and the last run heartbeat of one carousel."""

    phase_status: str
    heartbeat_at: datetime | None


@dataclass(frozen=True, kw_only=True)
class CarouselReviewRow:
    """Fields a review message quotes. ``output_dir`` holds the slide files."""

    topic: str
    caption: str
    output_dir: str | None
    # AE-0361: the review line quotes who the carousel is for and its preset.
    audience: str = ""
    niche: str = ""
    image_style: str = ""


def build_start_input(start: AutomationStart) -> EditorialWorkflowStartInput:
    """Engine start input with no reviewer."""
    return EditorialWorkflowStartInput(
        topic=start.topic,
        audience=start.audience,
        brief=start.brief,
        sources=[dict(source) for source in start.sources],
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
        """Insert the project and return its id."""
        created = await self._repo.create_project(project)
        return str(created.id)

    async def load_project(self, project_id: str) -> CarouselProject | None:
        """The carousel entity, or None when the id is unknown."""
        return await self._repo.get_project_by_id(UUID(project_id))

    async def slide_total(self, project_id: str) -> int:
        """Slides the project's config asks for. Zero when it does not exist."""
        project = await self.load_project(project_id)
        if project is None:
            return 0
        return slides_in_config(project.slides_config)

    async def heartbeat(self, project_id: str) -> RunHeartbeat | None:
        """Phase status and run heartbeat, or None when the row is missing."""
        row = await self._session.get(_carousel_model(), project_id)
        if row is None:
            return None
        return RunHeartbeat(
            phase_status=str(row.phase_status),
            heartbeat_at=row.run_heartbeat_at,
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
    "is_provider_outage",
    "slides_in_config",
]
