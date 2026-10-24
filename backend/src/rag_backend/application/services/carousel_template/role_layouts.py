"""Layout per slide role for "Ponto de Vista" decks (ADR-0021 D8).

Roles are positional in the project's sized contract, so the renderer reads
them from ``project_policy`` (never from persisted slide rows). Radar IA and
every legacy deck keep today's lookup (preferred strategy + structured fields).

``point`` slides keep the format's layout (``slide_layout_strategy``), and the twist has
no artwork in the contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from rag_backend.application.services.carousel.image_artwork import (
    artwork_slide_numbers,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    PresentationPolicyError,
)
from rag_backend.application.services.carousel.project_policy import project_policy
from rag_backend.application.services.carousel_template.strategies import (
    cta_follow,
    hook_face,
    insight_quote,
    news_quote,
    save_checklist,
    statement,
)
from rag_backend.domain.constants.news_quotes import INSIGHT_KEY
from rag_backend.domain.constants.presentation_roles import (
    ROLE_CTA,
    ROLE_HOOK,
    ROLE_POV,
    ROLE_REHOOK,
    ROLE_SAVE,
    ROLE_TWIST,
)
from rag_backend.domain.content_mode import is_pov_family, is_pov_news
from rag_backend.domain.models import CarouselProject

POV_ROLE_STRATEGIES: dict[str, str] = {
    ROLE_HOOK: hook_face.HOOK_FACE_STRATEGY,
    ROLE_REHOOK: statement.STATEMENT_STRATEGY,
    ROLE_POV: statement.STATEMENT_STRATEGY,
    ROLE_TWIST: statement.STATEMENT_STRATEGY,
    ROLE_SAVE: save_checklist.SAVE_CHECKLIST_STRATEGY,
    ROLE_CTA: cta_follow.CTA_FOLLOW_STRATEGY,
}


def pov_slide_strategies(project: CarouselProject, total_slides: int) -> dict[int, str]:
    """Slide number -> layout for a POV deck of ``total_slides``; {} otherwise."""
    if not is_pov_family(project.content_mode):
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


def checklist_slide_numbers(
    project: CarouselProject, slide_types: Mapping[int, str]
) -> frozenset[int]:
    """Slides whose structured items render as one-line checklist entries.

    Those show each item's single line (its title), not title plus body. The
    preferred layout is picked as the renderer does (the POV role layout, else the
    deck's chosen layout), and the checklist only renders the slide types it
    supports. ``slide_types`` maps slide number to slide type.
    """
    role_layouts = pov_slide_strategies(project, len(slide_types))
    checklist = save_checklist.SAVE_CHECKLIST_STRATEGY
    supported = save_checklist.SaveChecklistStrategy.supported_slide_types
    return frozenset(
        number
        for number, slide_type in slide_types.items()
        if slide_type in supported
        and (role_layouts.get(number) or project.slide_layout_strategy) == checklist
    )


def deck_artwork_slides(
    project: CarouselProject, total_slides: int
) -> frozenset[int] | None:
    """Slides of a ``total_slides`` deck the images phase illustrates.

    The same set the images node plans (``artwork_slide_numbers``), sized to the
    rendered deck, so the template never points at artwork that was never made.
    None for fixed contracts (every lower-third slide keeps its artwork).
    """
    return artwork_slide_numbers(replace(project, slide_count=total_slides))


def quote_card_strategy(
    project: CarouselProject, slide: Mapping[str, object]
) -> str | None:
    """A ``pov_news`` slide with a verified quote card -> ``insight_quote``.

    Takes precedence over the role layout (the twist is a statement slide
    otherwise), so the card is never silently dropped by the renderer.
    """
    if not is_pov_news(project.content_mode):
        return None
    if not news_quote.is_news_quote(slide.get(INSIGHT_KEY)):
        return None
    return insight_quote.INSIGHT_QUOTE_STRATEGY


__all__ = [
    "POV_ROLE_STRATEGIES",
    "checklist_slide_numbers",
    "deck_artwork_slides",
    "pov_slide_strategies",
    "quote_card_strategy",
]
