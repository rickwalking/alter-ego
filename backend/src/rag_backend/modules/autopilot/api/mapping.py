"""Map the HTTP topic batch to and from the intake use case."""

from __future__ import annotations

from rag_backend.domain.models.news_quote import NewsQuote
from rag_backend.modules.autopilot.api.schemas import (
    QuoteProposal,
    RejectedTopic,
    TopicBatch,
    TopicIntakeResponse,
    TopicProposal,
)
from rag_backend.modules.autopilot.application.topic_intake import (
    TopicIntakeCommand,
    TopicIntakeResult,
)
from rag_backend.modules.autopilot.domain.intake import ProposalInput
from rag_backend.modules.autopilot.domain.pov_choice import PovChoice


def command_from(batch: TopicBatch) -> TopicIntakeCommand:
    """Copy validated proposals into the use-case command."""
    proposals = tuple(_input(item, index) for index, item in enumerate(batch.topics))
    return TopicIntakeCommand(proposals=proposals)


def response_from(result: TopicIntakeResult) -> TopicIntakeResponse:
    """Copy the use-case result into the HTTP body."""
    rejected = [
        RejectedTopic(
            index=item.index, title=item.title, reason=item.reason, field=item.field
        )
        for item in result.rejected
    ]
    return TopicIntakeResponse(
        accepted=list(result.accepted),
        queued=list(result.queued),
        rejected=rejected,
    )


def _input(item: TopicProposal, index: int) -> ProposalInput:
    return ProposalInput(
        title=item.title,
        angle=item.angle,
        why_viral=item.why_viral,
        audience=item.audience,
        niche=item.niche,
        brief=item.brief,
        sources=tuple(item.sources),
        score=item.score,
        image_style=item.image_style,
        image_guidance=item.image_guidance,
        content_mode=item.mode,
        thesis_draft=item.thesis_draft,
        pov_choice=PovChoice(pov_format=item.pov_format, slide_count=item.slide_count),
        index=index,
        quotes=tuple(_quote(quote) for quote in item.quotes),
    )


def _quote(item: QuoteProposal) -> NewsQuote:
    return NewsQuote(
        quote_id=item.id,
        url=item.url,
        handle=item.handle,
        name=item.name,
        excerpt=item.excerpt,
        lang_original=item.lang_original,
        text_pt=item.text_pt,
        text_en=item.text_en,
    )
