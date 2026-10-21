"""The verified quotes a ``pov_news`` prompt may cite (ADR-0023).

Rows for the Jinja templates: the id the model may return as ``quote_id``,
who said it, and the PT text it may show. The text is case-preserving
sanitized data; the model never writes a quote, it only picks one by id.
"""

from __future__ import annotations

from rag_backend.domain.constants.news_quotes import (
    QUOTE_KEY_HANDLE,
    QUOTE_KEY_ID,
    QUOTE_KEY_NAME,
    QUOTE_KEY_TEXT_PT,
)
from rag_backend.domain.copy_sanitize import sanitize_model_copy
from rag_backend.domain.models.news_quote import NewsQuote


def quote_prompt_rows(quotes: tuple[NewsQuote, ...]) -> list[dict[str, str]]:
    """One template row per quote: id, name, handle and the PT text."""
    return [
        {
            QUOTE_KEY_ID: quote.quote_id,
            QUOTE_KEY_NAME: sanitize_model_copy(quote.name),
            QUOTE_KEY_HANDLE: sanitize_model_copy(quote.handle),
            QUOTE_KEY_TEXT_PT: sanitize_model_copy(quote.text_pt),
        }
        for quote in quotes
    ]


__all__ = ["quote_prompt_rows"]
