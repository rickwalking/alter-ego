"""Per-topic refusal rules of topic intake (split from ``intake.py``, AE-0406).

Pure. Each rule names the reason code and, when one field caused it, that
field (``audience``, ``quotes[1].excerpt``) so the scout can fix one topic
without guessing. The order is the contract's: text, URLs, sources, thesis,
the carousel defaults, the ``pov_news`` quotes, then (AE-0418) the cover.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from rag_backend.domain.content_mode import is_pov_family, is_pov_news
from rag_backend.domain.models.news_quote import NewsQuote
from rag_backend.modules.autopilot.carousel_constants import (
    REASON_AUDIENCE_NOT_SIMPLE,
    REASON_BRIEF_NOT_SIMPLE,
    REASON_BRIEF_OFF_THEME,
    REASON_IMAGE_STYLE_UNSUPPORTED,
    REASON_NICHE_NOT_SIMPLE,
)
from rag_backend.modules.autopilot.constants import (
    REASON_EMPTY_TEXT,
    REASON_SOURCE_NOT_IN_SIGNALS,
    REASON_URL_IN_TEXT,
)
from rag_backend.modules.autopilot.cover_constants import FIELD_COVER_ASSET_ID
from rag_backend.modules.autopilot.domain.carousel_defaults import (
    CarouselText,
    carousel_reason,
)
from rag_backend.modules.autopilot.domain.cover import (
    CoverCheck,
    CoverFacts,
    cover_reason,
)
from rag_backend.modules.autopilot.domain.quotes import QuoteFacts, quotes_problem
from rag_backend.modules.autopilot.domain.topic_text import contains_url
from rag_backend.modules.autopilot.intake_constants import (
    FIELD_ANGLE,
    FIELD_AUDIENCE,
    FIELD_BRIEF,
    FIELD_IMAGE_GUIDANCE,
    FIELD_IMAGE_STYLE,
    FIELD_NICHE,
    FIELD_SOURCES_TEMPLATE,
    FIELD_THESIS_DRAFT,
    FIELD_TITLE,
    FIELD_WHY_VIRAL,
)
from rag_backend.modules.autopilot.pov_constants import REASON_THESIS_MISSING
from rag_backend.modules.autopilot.quote_constants import (
    FIELD_QUOTES,
    REASON_QUOTE_INVALID,
)

# The field each carousel-default reason is about.
_CAROUSEL_FIELDS: dict[str, str] = {
    REASON_IMAGE_STYLE_UNSUPPORTED: FIELD_IMAGE_STYLE,
    REASON_AUDIENCE_NOT_SIMPLE: FIELD_AUDIENCE,
    REASON_NICHE_NOT_SIMPLE: FIELD_NICHE,
    REASON_BRIEF_NOT_SIMPLE: FIELD_BRIEF,
    REASON_BRIEF_OFF_THEME: FIELD_BRIEF,
}


@dataclass(frozen=True, kw_only=True)
class Refusal:
    """A reason code and the field that caused it (None = the topic as a whole)."""

    reason: str
    field: str | None = None


@dataclass(frozen=True, kw_only=True)
class TopicFields:
    """The stripped proposal fields the rules read."""

    title: str
    angle: str
    why_viral: str
    audience: str
    niche: str
    brief: str
    sources: tuple[str, ...]
    image_style: str
    image_guidance: str | None
    content_mode: str
    thesis_draft: str | None
    quotes: tuple[NewsQuote, ...] = ()
    # AE-0418: the GrokBot cover the topic names (None = no cover).
    cover_asset_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class RuleFacts:
    """The allowlist, stored X post texts and covers the rules check against."""

    allowlist: frozenset[str]
    post_texts: Mapping[str, str]
    covers: CoverFacts = field(default_factory=CoverFacts)


def refusal_for(topic: TopicFields, facts: RuleFacts) -> Refusal | None:
    """The first rule the topic breaks, or None when it may be stored."""
    for rule in (_blank, _url_in_text, _missing_source):
        found = rule(topic, facts)
        if found is not None:
            return found
    if is_pov_family(topic.content_mode) and not topic.thesis_draft:
        # AE-0377: a POV topic (``pov`` / ``pov_news``) needs the draft thesis.
        return Refusal(reason=REASON_THESIS_MISSING, field=FIELD_THESIS_DRAFT)
    carousel = _carousel_refusal(topic)
    if carousel is not None:
        return carousel
    return _quotes_refusal(topic, facts) or _cover_refusal(topic, facts)


def _named_text(topic: TopicFields) -> tuple[tuple[str, str], ...]:
    return (
        (FIELD_TITLE, topic.title),
        (FIELD_ANGLE, topic.angle),
        (FIELD_WHY_VIRAL, topic.why_viral),
        (FIELD_AUDIENCE, topic.audience),
        (FIELD_NICHE, topic.niche),
        (FIELD_BRIEF, topic.brief),
    )


def _blank(topic: TopicFields, _facts: RuleFacts) -> Refusal | None:
    for name, text in _named_text(topic):
        if text == "":
            return Refusal(reason=REASON_EMPTY_TEXT, field=name)
    return None


def _url_in_text(topic: TopicFields, _facts: RuleFacts) -> Refusal | None:
    texts = (
        *_named_text(topic),
        (FIELD_IMAGE_GUIDANCE, topic.image_guidance or ""),
        (FIELD_THESIS_DRAFT, topic.thesis_draft or ""),
    )
    for name, text in texts:
        if contains_url(text):
            return Refusal(reason=REASON_URL_IN_TEXT, field=name)
    return None


def _missing_source(topic: TopicFields, facts: RuleFacts) -> Refusal | None:
    for index, source in enumerate(topic.sources):
        if source not in facts.allowlist:
            return Refusal(
                reason=REASON_SOURCE_NOT_IN_SIGNALS,
                field=FIELD_SOURCES_TEMPLATE.format(index=index),
            )
    return None


def _carousel_refusal(topic: TopicFields) -> Refusal | None:
    reason = carousel_reason(
        CarouselText(
            title=topic.title,
            audience=topic.audience,
            niche=topic.niche,
            brief=topic.brief,
            image_style=topic.image_style,
        )
    )
    if reason is None:
        return None
    return Refusal(reason=reason, field=_CAROUSEL_FIELDS.get(reason))


def _quotes_refusal(topic: TopicFields, facts: RuleFacts) -> Refusal | None:
    """AE-0406: quotes belong to ``pov_news``; each one must be verified."""
    if not topic.quotes:
        return None
    if not is_pov_news(topic.content_mode):
        return Refusal(reason=REASON_QUOTE_INVALID, field=FIELD_QUOTES)
    problem = quotes_problem(
        topic.quotes,
        QuoteFacts(sources=frozenset(topic.sources), post_texts=facts.post_texts),
    )
    if problem is None:
        return None
    return Refusal(reason=problem.reason, field=problem.field)


def _cover_refusal(topic: TopicFields, facts: RuleFacts) -> Refusal | None:
    """AE-0418: the cover must exist, be fresh, unused, and (screenshot) sourced."""
    if topic.cover_asset_id is None:
        return None
    reason = cover_reason(
        CoverCheck(asset_id=topic.cover_asset_id, sources=topic.sources),
        facts.covers,
    )
    if reason is None:
        return None
    return Refusal(reason=reason, field=FIELD_COVER_ASSET_ID)


__all__ = ["Refusal", "RuleFacts", "TopicFields", "refusal_for"]
