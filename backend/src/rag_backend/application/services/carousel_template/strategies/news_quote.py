"""The ``pov_news`` quote card: verbatim quote + attribution row.

Phase 1 of spec §4: an initial-letter circle (accent fill, first letter of
``name``), the name, and ``@handle · X``. Never a URL. Every value comes from
the stored, scout-verified quote, escaped here.
"""

from __future__ import annotations

import html
from collections.abc import Mapping

from rag_backend.domain.constants.news_quotes import (
    ATTRIBUTION_HANDLE_TEMPLATE,
    CARD_KEY_HANDLE,
    CARD_KEY_NAME,
    CARD_KEY_QUOTE,
)


def _text(insight: Mapping[str, object], key: str) -> str:
    value = insight.get(key)
    return value.strip() if isinstance(value, str) else ""


def is_news_quote(insight: object) -> bool:
    """True for a card that carries a quoted account (name and handle)."""
    if not isinstance(insight, Mapping):
        return False
    return bool(_text(insight, CARD_KEY_QUOTE) and _text(insight, CARD_KEY_HANDLE))


def attribution_row_html(insight: Mapping[str, object]) -> str:
    """Initial circle, name and ``@handle · X``."""
    name = _text(insight, CARD_KEY_NAME) or _text(insight, CARD_KEY_HANDLE)
    handle = _text(insight, CARD_KEY_HANDLE)
    initial = html.escape(name[:1].upper())
    return (
        '<div class="quote-attribution">'
        f'<span class="quote-avatar" aria-hidden="true">{initial}</span>'
        f'<span class="quote-name">{html.escape(name)}</span>'
        f'<span class="quote-handle">'
        f"{html.escape(ATTRIBUTION_HANDLE_TEMPLATE.format(handle=handle))}</span>"
        "</div>"
    )


def news_quote_card_html(insight: Mapping[str, object]) -> str:
    """The card: the quote text, verbatim (escaped, no inline markup), then the row."""
    quote = html.escape(_text(insight, CARD_KEY_QUOTE))
    return (
        f'<figure class="insight-card pov-quote-card">'
        f'<blockquote class="quote-text">{quote}</blockquote>'
        f"{attribution_row_html(insight)}</figure>"
    )


__all__ = ["attribution_row_html", "is_news_quote", "news_quote_card_html"]
