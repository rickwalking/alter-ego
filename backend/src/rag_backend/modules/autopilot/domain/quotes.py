"""Verify the scout's quotes on one ``pov_news`` topic (AE-0406, spec §4).

Pure: the caller supplies the topic's canonical sources and the post texts the
backend stored through ``POST /x-signals``. The first problem found rejects the
topic (never the batch) with its reason code and the field that caused it.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from rag_backend.domain.models.news_quote import NewsQuote
from rag_backend.modules.autopilot.constants import REASON_URL_IN_TEXT
from rag_backend.modules.autopilot.domain.quote_text import (
    excerpt_in_post,
    word_count,
)
from rag_backend.modules.autopilot.domain.topic_text import contains_url, strip_controls
from rag_backend.modules.autopilot.domain.x_status import parse_status_url
from rag_backend.modules.autopilot.quote_constants import (
    FIELD_EXCERPT,
    FIELD_HANDLE,
    FIELD_ID,
    FIELD_LANG,
    FIELD_NAME,
    FIELD_QUOTE_TEMPLATE,
    FIELD_QUOTES,
    FIELD_TEXT_EN,
    FIELD_TEXT_PT,
    FIELD_URL,
    QUOTE_EXCERPT_MAX_CHARS,
    QUOTE_ID_PATTERN,
    QUOTE_LANGUAGES,
    QUOTE_NAME_MAX_CHARS,
    QUOTE_TEXT_EN_MAX_WORDS,
    QUOTE_TEXT_PT_MAX_WORDS,
    QUOTES_MAX,
    REASON_QUOTE_HANDLE_MISMATCH,
    REASON_QUOTE_INVALID,
    REASON_QUOTE_NOT_IN_POST,
    REASON_QUOTE_SOURCE_INVALID,
    REASON_QUOTE_TOO_LONG,
)

_QUOTE_ID = re.compile(QUOTE_ID_PATTERN)


@dataclass(frozen=True, kw_only=True)
class QuoteProblem:
    """Why a topic's quotes were refused, and which field caused it."""

    reason: str
    field: str


@dataclass(frozen=True, kw_only=True)
class QuoteFacts:
    """What the quotes are checked against: the topic sources and stored posts."""

    sources: frozenset[str]
    post_texts: Mapping[str, str]


@dataclass(frozen=True, kw_only=True)
class _Check:
    quote: NewsQuote
    index: int
    facts: QuoteFacts


_Rule = tuple[str, str, Callable[[_Check], bool]]


def clean_quote(quote: NewsQuote) -> NewsQuote:
    """Strip control characters and surrounding whitespace from every field."""
    return NewsQuote(
        quote_id=strip_controls(quote.quote_id),
        url=strip_controls(quote.url),
        handle=strip_controls(quote.handle),
        name=strip_controls(quote.name),
        excerpt=quote.excerpt.strip(),
        lang_original=strip_controls(quote.lang_original),
        text_pt=strip_controls(quote.text_pt),
        text_en=strip_controls(quote.text_en),
    )


def quotes_problem(
    quotes: tuple[NewsQuote, ...], facts: QuoteFacts
) -> QuoteProblem | None:
    """The first rule the quotes break, or None when every quote is verified."""
    if len(quotes) > QUOTES_MAX:
        return QuoteProblem(reason=REASON_QUOTE_INVALID, field=FIELD_QUOTES)
    seen: set[str] = set()
    for index, quote in enumerate(quotes):
        if quote.quote_id in seen:
            return _problem(REASON_QUOTE_INVALID, index, FIELD_ID)
        seen.add(quote.quote_id)
        problem = _quote_problem(_Check(quote=quote, index=index, facts=facts))
        if problem is not None:
            return problem
    return None


def quote_urls(quotes: tuple[NewsQuote, ...]) -> tuple[str, ...]:
    """The canonical status URLs the quotes cite (unparseable URLs left out)."""
    targets = (parse_status_url(quote.url) for quote in quotes)
    return tuple(target.canonical_url for target in targets if target is not None)


def _problem(reason: str, index: int, name: str) -> QuoteProblem:
    return QuoteProblem(
        reason=reason, field=FIELD_QUOTE_TEMPLATE.format(index=index, name=name)
    )


def _quote_problem(check: _Check) -> QuoteProblem | None:
    for reason, name, passes in _RULES:
        if not passes(check):
            return _problem(reason, check.index, name)
    return None


def _id_ok(check: _Check) -> bool:
    return _QUOTE_ID.fullmatch(check.quote.quote_id) is not None


def _name_ok(check: _Check) -> bool:
    return 0 < len(check.quote.name) <= QUOTE_NAME_MAX_CHARS


def _lang_ok(check: _Check) -> bool:
    return check.quote.lang_original in QUOTE_LANGUAGES


def _source_ok(check: _Check) -> bool:
    """A canonical X status URL, listed in sources, stored through x-signals."""
    url = check.quote.url
    target = parse_status_url(url)
    if target is None or target.canonical_url != url:
        return False
    return url in check.facts.sources and url in check.facts.post_texts


def _handle_ok(check: _Check) -> bool:
    target = parse_status_url(check.quote.url)
    handle = target.handle if target is not None else ""
    return check.quote.handle.casefold() == handle.casefold()


def _excerpt_ok(check: _Check) -> bool:
    excerpt = check.quote.excerpt
    if not 0 < len(excerpt) <= QUOTE_EXCERPT_MAX_CHARS:
        return False
    return excerpt_in_post(excerpt, check.facts.post_texts.get(check.quote.url, ""))


def _present(value: str) -> bool:
    return value != ""


def _no_url(value: str) -> bool:
    return not contains_url(value)


_RULES: tuple[_Rule, ...] = (
    (REASON_QUOTE_INVALID, FIELD_ID, _id_ok),
    (REASON_QUOTE_INVALID, FIELD_NAME, _name_ok),
    (REASON_QUOTE_INVALID, FIELD_LANG, _lang_ok),
    (REASON_QUOTE_INVALID, FIELD_TEXT_PT, lambda c: _present(c.quote.text_pt)),
    (REASON_QUOTE_INVALID, FIELD_TEXT_EN, lambda c: _present(c.quote.text_en)),
    (REASON_URL_IN_TEXT, FIELD_NAME, lambda c: _no_url(c.quote.name)),
    (REASON_URL_IN_TEXT, FIELD_EXCERPT, lambda c: _no_url(c.quote.excerpt)),
    (REASON_URL_IN_TEXT, FIELD_TEXT_PT, lambda c: _no_url(c.quote.text_pt)),
    (REASON_URL_IN_TEXT, FIELD_TEXT_EN, lambda c: _no_url(c.quote.text_en)),
    (REASON_QUOTE_SOURCE_INVALID, FIELD_URL, _source_ok),
    (REASON_QUOTE_HANDLE_MISMATCH, FIELD_HANDLE, _handle_ok),
    (REASON_QUOTE_NOT_IN_POST, FIELD_EXCERPT, _excerpt_ok),
    (
        REASON_QUOTE_TOO_LONG,
        FIELD_TEXT_PT,
        lambda c: word_count(c.quote.text_pt) <= QUOTE_TEXT_PT_MAX_WORDS,
    ),
    (
        REASON_QUOTE_TOO_LONG,
        FIELD_TEXT_EN,
        lambda c: word_count(c.quote.text_en) <= QUOTE_TEXT_EN_MAX_WORDS,
    ),
)

__all__ = [
    "QuoteFacts",
    "QuoteProblem",
    "clean_quote",
    "quote_urls",
    "quotes_problem",
]
