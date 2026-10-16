"""A scout-verified quote of an X post (AE-0406, ADR-0023, spec §4).

The autopilot intake checks every field against the post text stored through
``POST /x-signals`` before a quote reaches a topic. From there it rides the
run onto the carousel project (``pov_quotes``) as plain JSON rows; the content
phase may place ``text_pt`` / ``text_en`` verbatim, and the renderer draws the
attribution from ``name`` and ``handle`` (never a URL).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from rag_backend.domain.constants.news_quotes import (
    QUOTE_KEY_EXCERPT,
    QUOTE_KEY_HANDLE,
    QUOTE_KEY_ID,
    QUOTE_KEY_LANG,
    QUOTE_KEY_NAME,
    QUOTE_KEY_TEXT_EN,
    QUOTE_KEY_TEXT_PT,
    QUOTE_KEY_URL,
)


@dataclass(frozen=True, kw_only=True)
class NewsQuote:
    """One verified quote: who said it, the exact excerpt, and both renderings."""

    quote_id: str
    url: str
    handle: str
    name: str
    excerpt: str
    lang_original: str
    text_pt: str
    text_en: str

    def to_row(self) -> dict[str, str]:
        """The JSON row stored on ``topic_candidates.quotes`` / ``pov_quotes``."""
        return {
            QUOTE_KEY_ID: self.quote_id,
            QUOTE_KEY_URL: self.url,
            QUOTE_KEY_HANDLE: self.handle,
            QUOTE_KEY_NAME: self.name,
            QUOTE_KEY_EXCERPT: self.excerpt,
            QUOTE_KEY_LANG: self.lang_original,
            QUOTE_KEY_TEXT_PT: self.text_pt,
            QUOTE_KEY_TEXT_EN: self.text_en,
        }


def quote_from_row(row: dict[str, object]) -> NewsQuote | None:
    """The quote stored in ``row``; None when a field is missing or not text."""
    values = {key: row.get(key) for key in _ROW_KEYS}
    if not all(isinstance(value, str) for value in values.values()):
        return None
    text = {key: str(value) for key, value in values.items()}
    return NewsQuote(
        quote_id=text[QUOTE_KEY_ID],
        url=text[QUOTE_KEY_URL],
        handle=text[QUOTE_KEY_HANDLE],
        name=text[QUOTE_KEY_NAME],
        excerpt=text[QUOTE_KEY_EXCERPT],
        lang_original=text[QUOTE_KEY_LANG],
        text_pt=text[QUOTE_KEY_TEXT_PT],
        text_en=text[QUOTE_KEY_TEXT_EN],
    )


def quotes_from_rows(rows: object) -> tuple[NewsQuote, ...]:
    """Every well-formed quote in a stored JSON list (None / junk -> empty)."""
    if not isinstance(rows, list):
        return ()
    parsed = (quote_from_row(row) for row in rows if isinstance(row, dict))
    return tuple(quote for quote in parsed if quote is not None)


def quote_rows(quotes: Iterable[NewsQuote]) -> list[dict[str, str]]:
    """The JSON list for ``quotes`` (empty list when there are none)."""
    return [quote.to_row() for quote in quotes]


_ROW_KEYS: tuple[str, ...] = (
    QUOTE_KEY_ID,
    QUOTE_KEY_URL,
    QUOTE_KEY_HANDLE,
    QUOTE_KEY_NAME,
    QUOTE_KEY_EXCERPT,
    QUOTE_KEY_LANG,
    QUOTE_KEY_TEXT_PT,
    QUOTE_KEY_TEXT_EN,
)

__all__ = [
    "NewsQuote",
    "quote_from_row",
    "quote_rows",
    "quotes_from_rows",
]
