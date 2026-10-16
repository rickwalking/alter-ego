"""The verified quotes a ``pov_news`` prompt may cite (AE-0406, ADR-0023).

Rows for the Jinja templates: the id the model may return as ``quote_id``,
who said it, and the PT text it may show. The text is case-preserving
sanitized data; the model never writes a quote, it only picks one by id.
"""

from __future__ import annotations

from rag_backend.domain.copy_sanitize import sanitize_model_copy
from rag_backend.domain.models.news_quote import NewsQuote


def quote_prompt_rows(quotes: tuple[NewsQuote, ...]) -> list[dict[str, str]]:
    """One template row per quote: id, name, handle and the PT text."""
    return [
        {
            "id": quote.quote_id,
            "name": sanitize_model_copy(quote.name),
            "handle": sanitize_model_copy(quote.handle),
            "text_pt": sanitize_model_copy(quote.text_pt),
        }
        for quote in quotes
    ]


__all__ = ["quote_prompt_rows"]
