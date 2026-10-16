"""What the generators need to know about a project's content mode (AE-0375).

ADR-0021 D4: the mode is read from the project row at generation time, not
threaded through the LangGraph state, so manual, autopilot and resumed runs
see the same thesis. The POV inputs are create-only; ``hook_text`` is the
owner's pick at the outline gate.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.editorial_distribution_pack import (
    load_carousel_project,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
    PresentationPolicyError,
)
from rag_backend.application.services.carousel.project_policy import project_policy
from rag_backend.application.services.carousel_template.cta_copy import cta_copy
from rag_backend.domain.constants.carousel import LANGUAGE_PT
from rag_backend.domain.constants.carousel_cta import DEFAULT_CTA_HANDLE
from rag_backend.domain.constants.content_mode import (
    DEFAULT_CONTENT_MODE,
    DEFAULT_POV_FORMAT,
)
from rag_backend.domain.content_mode import is_pov_family, pov_prompt_domain
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.news_quote import NewsQuote

logger = structlog.get_logger(__name__)

LOG_BRIEF_UNAVAILABLE = "content_mode_brief_unavailable"


@dataclass(frozen=True, kw_only=True)
class ContentModeBrief:
    """A project's mode, its sized contract and the owner's POV inputs."""

    content_mode: str
    policy: CarouselPresentationPolicy
    thesis: str = ""
    personal_proof: str = ""
    pov_format: str = DEFAULT_POV_FORMAT
    cta_goal: str | None = None
    hook_text: str = ""
    creator_handle: str = DEFAULT_CTA_HANDLE
    # AE-0406: the scout-verified quotes of a ``pov_news`` project.
    quotes: tuple[NewsQuote, ...] = ()

    @property
    def is_pov(self) -> bool:
        """True for a POV-family project (``pov`` and ``pov_news``)."""
        return is_pov_family(self.content_mode)

    @property
    def prompt_domain(self) -> str:
        """AE-0406: the POV prompt family that voices this project."""
        return pov_prompt_domain(self.content_mode)

    @property
    def has_roles(self) -> bool:
        """True when the contract stamps roles (POV and Radar IA v4)."""
        return self.policy.has_roles

    def role_at(self, slide_index: int) -> str | None:
        """The role of a 1-based slide index in the sized contract."""
        for slide in self.policy.slides:
            if slide.slide_number == slide_index:
                return slide.role
        return None

    def cta_sentence(self) -> str:
        """The CTA slide sentence for this project's goal (PT)."""
        return cta_copy(self.cta_goal, LANGUAGE_PT, self.creator_handle)


def brief_for_project(project: CarouselProject) -> ContentModeBrief:
    """Build the brief from a loaded project (sizes its contract)."""
    return ContentModeBrief(
        content_mode=project.content_mode or DEFAULT_CONTENT_MODE,
        policy=project_policy(project),
        thesis=project.pov_thesis or "",
        personal_proof=project.pov_personal_proof or "",
        pov_format=project.pov_format or DEFAULT_POV_FORMAT,
        cta_goal=project.cta_goal,
        hook_text=project.hook_text or "",
        creator_handle=project.creator_handle or DEFAULT_CTA_HANDLE,
        quotes=project.pov_quotes,
    )


async def load_content_mode_brief(
    db: AsyncSession | None, project_id: str
) -> ContentModeBrief | None:
    """The brief for ``project_id``; None without a session, project or contract.

    None keeps the generators on the legacy (fixed 7-slide) path, which is
    exactly today's behaviour for every project without a stamped contract.
    """
    if db is None or not project_id:
        return None
    project = await load_carousel_project(db, project_id)
    if project is None:
        return None
    try:
        return brief_for_project(project)
    except PresentationPolicyError:
        logger.warning(LOG_BRIEF_UNAVAILABLE, project_id=project_id)
        return None


__all__ = [
    "ContentModeBrief",
    "brief_for_project",
    "load_content_mode_brief",
]
