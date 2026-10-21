"""The autopilot content gate re-checks ``pov_news`` quote cards.

A quote card is placed by code from the verified quotes, so this never fires
on a healthy run. It is the deterministic backstop of spec §4: a card whose
text is not exactly the supplied ``text_pt`` / ``text_en`` (or a third card)
blocks the gate and escalates to the owner instead of being approved.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from rag_backend.domain.constants.news_quotes import (
    MSG_QUOTE_NOT_VERBATIM,
    MSG_TOO_MANY_QUOTE_CARDS,
    RULE_TOO_MANY_QUOTE_CARDS,
)
from rag_backend.domain.content_mode import is_pov_news
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.news_quote_cards import QuoteCardProblem, quote_card_problems
from rag_backend.modules.autopilot.domain.gate import QualityViolation
from rag_backend.modules.autopilot.quality_constants import FIELD_LOCALIZED_SLIDES


class ProjectLoader(Protocol):
    """The editorial ACL call this check needs (``CarouselAutomationAcl``)."""

    async def load_project(self, project_id: str) -> CarouselProject | None:
        """The carousel entity, or None when the id is unknown."""
        ...


async def quote_violations(
    acl: ProjectLoader, project_id: str, state: Mapping[str, object]
) -> tuple[QualityViolation, ...]:
    """The blocking quote-card problems of a ``pov_news`` carousel (else none)."""
    project = await acl.load_project(project_id)
    if project is None or not is_pov_news(project.content_mode):
        return ()
    problems = quote_card_problems(
        _slides(state.get(FIELD_LOCALIZED_SLIDES)), project.pov_quotes
    )
    return tuple(_violation(problem) for problem in problems)


def _slides(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _violation(problem: QuoteCardProblem) -> QualityViolation:
    message = (
        MSG_TOO_MANY_QUOTE_CARDS
        if problem.rule == RULE_TOO_MANY_QUOTE_CARDS
        else MSG_QUOTE_NOT_VERBATIM
    )
    return QualityViolation(
        rule=problem.rule,
        slide_index=problem.slide_index,
        locale=problem.locale,
        message=message,
    )


__all__ = ["ProjectLoader", "quote_violations"]
