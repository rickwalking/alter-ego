"""Quote cards of ``pov_news`` decks (AE-0406, ADR-0023, spec §4). Pure.

The content model never writes a quote: on a point or twist slide it may
return ``quote_id``. Code then places the card with the supplied text, verbatim
(``text_pt`` on PT, ``text_en`` on EN), keeps at most two cards per deck, and
checks every card again before the autopilot approves the content gate.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.domain.constants.news_quotes import (
    CARD_KEY_ATTRIBUTION,
    CARD_KEY_HANDLE,
    CARD_KEY_NAME,
    CARD_KEY_QUOTE,
    CARD_KEY_QUOTE_ID,
    INSIGHT_KEY,
    LOCALE_EN,
    LOCALE_PT,
    MAX_QUOTE_CARDS,
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    QUOTE_CARD_ROLES,
    RULE_QUOTE_NOT_VERBATIM,
    RULE_TOO_MANY_QUOTE_CARDS,
    SLIDE_INDEX_KEY,
    SLIDE_ROLE_KEY,
)
from rag_backend.domain.models.news_quote import NewsQuote

_LOCALES: tuple[tuple[str, str], ...] = (
    (PRESENTATION_PT_KEY, LOCALE_PT),
    (PRESENTATION_EN_KEY, LOCALE_EN),
)


@dataclass(frozen=True, kw_only=True)
class QuoteCardProblem:
    """A card that is not a supplied quote, or one card too many."""

    rule: str
    slide_index: int | None = None
    locale: str = ""


@dataclass
class _Placement:
    by_id: Mapping[str, NewsQuote]
    used: set[str]


def quote_card(quote: NewsQuote, text: str) -> dict[str, str]:
    """The ``insight`` dict for ``quote`` shown as ``text``."""
    return {
        CARD_KEY_QUOTE: text,
        CARD_KEY_ATTRIBUTION: quote.name,
        CARD_KEY_NAME: quote.name,
        CARD_KEY_HANDLE: quote.handle,
        CARD_KEY_QUOTE_ID: quote.quote_id,
    }


def place_quote_cards(
    drafts: list[dict[str, object]], quotes: tuple[NewsQuote, ...]
) -> list[dict[str, object]]:
    """Each draft with its PT card (or none). Model-written insights are dropped."""
    placement = _Placement(by_id={q.quote_id: q for q in quotes}, used=set())
    return [_placed(draft, placement) for draft in drafts]


def with_en_quote_cards(
    translations: dict[int, dict[str, object]],
    drafts: list[dict[str, object]],
    quotes: tuple[NewsQuote, ...],
) -> dict[int, dict[str, object]]:
    """The EN translations with the EN card of every placed PT card."""
    by_id = {quote.quote_id: quote for quote in quotes}
    result = dict(translations)
    for draft in drafts:
        quote = _card_quote(draft.get(INSIGHT_KEY), by_id)
        index = draft.get(SLIDE_INDEX_KEY)
        if quote is None or not isinstance(index, int) or index not in result:
            continue
        result[index] = {**result[index], INSIGHT_KEY: quote_card(quote, quote.text_en)}
    return result


def quote_card_problems(
    localized_slides: list[dict[str, object]], quotes: tuple[NewsQuote, ...]
) -> list[QuoteCardProblem]:
    """Every card that is not verbatim, plus a deck-wide problem past two cards."""
    by_id = {quote.quote_id: quote for quote in quotes}
    problems = [
        problem
        for slide in localized_slides
        for problem in _slide_problems(slide, by_id)
    ]
    cards = sum(
        1 for slide in localized_slides if _insight(slide.get(PRESENTATION_PT_KEY))
    )
    if cards > MAX_QUOTE_CARDS:
        problems.append(QuoteCardProblem(rule=RULE_TOO_MANY_QUOTE_CARDS))
    return problems


def _slide_problems(
    slide: dict[str, object], by_id: Mapping[str, NewsQuote]
) -> list[QuoteCardProblem]:
    index = slide.get(SLIDE_INDEX_KEY)
    slide_index = index if isinstance(index, int) else None
    problems: list[QuoteCardProblem] = []
    for key, locale in _LOCALES:
        insight = _insight(slide.get(key))
        if insight is not None and not _verbatim(insight, by_id, locale):
            problems.append(_problem(slide_index, locale))
    return problems


def _placed(draft: dict[str, object], placement: _Placement) -> dict[str, object]:
    slide = dict(draft)
    slide.pop(INSIGHT_KEY, None)
    quote_id = slide.pop(CARD_KEY_QUOTE_ID, None)
    quote = placement.by_id.get(quote_id) if isinstance(quote_id, str) else None
    if quote is None or not _may_place(slide, quote, placement):
        return slide
    placement.used.add(quote.quote_id)
    slide[INSIGHT_KEY] = quote_card(quote, quote.text_pt)
    return slide


def _may_place(
    slide: dict[str, object], quote: NewsQuote, placement: _Placement
) -> bool:
    if slide.get(SLIDE_ROLE_KEY) not in QUOTE_CARD_ROLES:
        return False
    if quote.quote_id in placement.used:
        return False
    return len(placement.used) < MAX_QUOTE_CARDS


def _card_quote(raw: object, by_id: Mapping[str, NewsQuote]) -> NewsQuote | None:
    if not isinstance(raw, dict):
        return None
    quote_id = raw.get(CARD_KEY_QUOTE_ID)
    return by_id.get(quote_id) if isinstance(quote_id, str) else None


def _insight(payload: object) -> dict[str, object] | None:
    if not isinstance(payload, dict):
        return None
    insight = payload.get(INSIGHT_KEY)
    if not isinstance(insight, dict) or not insight.get(CARD_KEY_QUOTE):
        return None
    return insight


def _verbatim(
    insight: dict[str, object], by_id: Mapping[str, NewsQuote], locale: str
) -> bool:
    quote = _card_quote(insight, by_id)
    if quote is None:
        return False
    expected = quote.text_pt if locale == LOCALE_PT else quote.text_en
    return insight.get(CARD_KEY_QUOTE) == expected


def _problem(slide_index: int | None, locale: str) -> QuoteCardProblem:
    return QuoteCardProblem(
        rule=RULE_QUOTE_NOT_VERBATIM, slide_index=slide_index, locale=locale
    )


__all__ = [
    "QuoteCardProblem",
    "place_quote_cards",
    "quote_card",
    "quote_card_problems",
    "with_en_quote_cards",
]
