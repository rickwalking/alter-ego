"""Shared builders for the ``pov_news`` quote tests."""

from __future__ import annotations

from dataclasses import replace

from rag_backend.domain.models.news_quote import NewsQuote
from rag_backend.modules.autopilot.domain.intake import ProposalInput

POST_URL = "https://x.com/kanishksj01/status/1234567890"
OTHER_URL = "https://x.com/alexcovo_eth/status/1234567891"
NEWS_URL = "https://www.anthropic.com/news/agents"
POST_TEXT = (
    "In just a day I have run hundreds of cloud agents in parallel across all "
    "the lessons in my physics learning app."
)
EXCERPT = "In just a day I have run hundreds of cloud agents in parallel"
THESIS = "Agentes em paralelo não são um ganho de código, são um gargalo de revisão."


def quote(**changes: str) -> NewsQuote:
    """The spec §4 example quote, with ``changes`` applied."""
    base = NewsQuote(
        quote_id="q1",
        url=POST_URL,
        handle="kanishksj01",
        name="Kanishk Jain",
        excerpt=EXCERPT,
        lang_original="en",
        text_pt="Em um só dia, rodei centenas de agentes na nuvem em paralelo.",
        text_en="In one day I ran hundreds of cloud agents in parallel.",
    )
    return replace(base, **changes)


def news_proposal(
    *quotes: NewsQuote, index: int = 0, title: str = "Agentes em paralelo"
) -> ProposalInput:
    """A ``pov_news`` proposal citing the post, with ``quotes``."""
    return ProposalInput(
        title=title,
        angle="Rodar centenas de agentes empurra o custo para a revisão.",
        why_viral="Devs postam números de agentes em paralelo.",
        audience="devs",
        niche="agentes de IA",
        brief=f"Relatos recentes sobre {title.lower()} e o custo de revisão.",
        sources=(POST_URL, OTHER_URL),
        score=78,
        content_mode="pov_news",
        thesis_draft=THESIS,
        index=index,
        quotes=quotes,
    )


__all__ = [
    "EXCERPT",
    "NEWS_URL",
    "OTHER_URL",
    "POST_TEXT",
    "POST_URL",
    "THESIS",
    "news_proposal",
    "quote",
]
