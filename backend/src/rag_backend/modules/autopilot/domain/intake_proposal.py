"""Scout proposals before and after preparation (split from ``intake.py``).

``prepare`` strips control characters, canonicalizes sources and computes the
signal hash. It also carries the optional GrokBot cover the topic names.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag_backend.domain.constants.content_mode import CONTENT_MODE_NEWS_ANALYSIS
from rag_backend.domain.models.news_quote import NewsQuote
from rag_backend.modules.autopilot.domain.carousel_defaults import DEFAULT_IMAGE_STYLE
from rag_backend.modules.autopilot.domain.cover import parse_asset_id
from rag_backend.modules.autopilot.domain.pov_choice import (
    NO_POV_CHOICE,
    PovChoice,
    pov_choice_for,
)
from rag_backend.modules.autopilot.domain.quotes import clean_quote
from rag_backend.modules.autopilot.domain.topic_text import signal_hash, strip_controls
from rag_backend.modules.autopilot.domain.x_status import canonical_url


@dataclass(frozen=True, kw_only=True)
class ProposalInput:
    """One schema-valid proposal before control-character stripping.

    No ``content_mode`` means Radar IA; POV needs the draft thesis. ``index`` is the
    topic's index in the request; ``quotes`` are the ``pov_news`` quotes and
    ``cover_asset_id`` the GrokBot cover the topic names (``cover.asset_id``).
    """

    title: str
    angle: str
    why_viral: str
    audience: str
    niche: str
    brief: str
    sources: tuple[str, ...]
    score: int
    image_style: str = DEFAULT_IMAGE_STYLE
    image_guidance: str | None = None
    content_mode: str = CONTENT_MODE_NEWS_ANALYSIS
    thesis_draft: str | None = None
    pov_choice: PovChoice = NO_POV_CHOICE
    index: int = 0
    quotes: tuple[NewsQuote, ...] = ()
    cover_asset_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class PreparedProposal:
    """A proposal after stripping and canonicalizing sources."""

    raw_title: str
    title: str
    angle: str
    why_viral: str
    audience: str
    niche: str
    brief: str
    sources: tuple[str, ...]
    score: int
    signal_hash: str
    image_style: str = DEFAULT_IMAGE_STYLE
    image_guidance: str | None = None
    content_mode: str = CONTENT_MODE_NEWS_ANALYSIS
    thesis_draft: str | None = None
    pov_choice: PovChoice = NO_POV_CHOICE
    index: int = 0
    quotes: tuple[NewsQuote, ...] = ()
    cover_asset_id: str | None = None

    @property
    def cover_uuid(self) -> UUID | None:
        """The named cover as a UUID (None when absent or malformed)."""
        if self.cover_asset_id is None:
            return None
        return parse_asset_id(self.cover_asset_id)

    @property
    def is_news(self) -> bool:
        """True for a Radar IA proposal (capped per week; ``pov_news`` is not)."""
        return self.content_mode == CONTENT_MODE_NEWS_ANALYSIS


def prepare(proposal: ProposalInput) -> PreparedProposal:
    """Strip control characters and canonicalize source URLs."""
    title = strip_controls(proposal.title)
    sources = tuple(
        canonical_url(strip_controls(source)) for source in proposal.sources
    )
    return PreparedProposal(
        raw_title=proposal.title,
        title=title,
        angle=strip_controls(proposal.angle),
        why_viral=strip_controls(proposal.why_viral),
        audience=strip_controls(proposal.audience),
        niche=strip_controls(proposal.niche),
        brief=strip_controls(proposal.brief),
        sources=sources,
        score=proposal.score,
        signal_hash=signal_hash(title, sources),
        image_style=proposal.image_style,
        image_guidance=_optional_text(proposal.image_guidance),
        content_mode=proposal.content_mode,
        thesis_draft=_optional_text(proposal.thesis_draft),
        pov_choice=pov_choice_for(proposal.content_mode, proposal.pov_choice),
        index=proposal.index,
        quotes=tuple(clean_quote(quote) for quote in proposal.quotes),
        cover_asset_id=_optional_text(proposal.cover_asset_id),
    )


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return strip_controls(value) or None


__all__ = ["PreparedProposal", "ProposalInput", "prepare"]
