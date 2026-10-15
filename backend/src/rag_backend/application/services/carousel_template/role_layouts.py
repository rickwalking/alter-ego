"""Layout per slide role for "Ponto de Vista" decks (AE-0376, ADR-0021 D8).

Roles are positional in the project's sized contract, so the renderer reads
them from ``project_policy`` (never from persisted slide rows). Radar IA and
every legacy deck keep today's lookup (preferred strategy + structured fields).
"""

from __future__ import annotations

from dataclasses import replace

from rag_backend.application.services.carousel.presentation_policy_types import (
    PresentationPolicyError,
)
from rag_backend.application.services.carousel.project_policy import project_policy
from rag_backend.application.services.carousel_template.strategies import (
    cta_follow,
    hook_face,
    save_checklist,
    statement,
)
from rag_backend.domain.constants.content_mode import CONTENT_MODE_POV
from rag_backend.domain.constants.presentation_roles import (
    ROLE_CTA,
    ROLE_HOOK,
    ROLE_POV,
    ROLE_REHOOK,
    ROLE_SAVE,
    ROLE_TWIST,
)
from rag_backend.domain.models import CarouselProject

INSIGHT_QUOTE_STRATEGY = "insight_quote"
# ``point`` slides keep the format's layout (``slide_layout_strategy``).
POV_ROLE_STRATEGIES: dict[str, str] = {
    ROLE_HOOK: hook_face.HOOK_FACE_STRATEGY,
    ROLE_REHOOK: statement.STATEMENT_STRATEGY,
    ROLE_POV: statement.STATEMENT_STRATEGY,
    ROLE_TWIST: INSIGHT_QUOTE_STRATEGY,
    ROLE_SAVE: save_checklist.SAVE_CHECKLIST_STRATEGY,
    ROLE_CTA: cta_follow.CTA_FOLLOW_STRATEGY,
}


def pov_slide_strategies(project: CarouselProject, total_slides: int) -> dict[int, str]:
    """Slide number -> layout for a POV deck of ``total_slides``; {} otherwise."""
    if project.content_mode != CONTENT_MODE_POV:
        return {}
    sized = replace(project, slide_count=total_slides)
    try:
        policy = project_policy(sized)
    except PresentationPolicyError:
        return {}
    return {
        slide.slide_number: POV_ROLE_STRATEGIES[slide.role]
        for slide in policy.slides
        if slide.role in POV_ROLE_STRATEGIES
    }


__all__ = ["INSIGHT_QUOTE_STRATEGY", "POV_ROLE_STRATEGIES", "pov_slide_strategies"]
