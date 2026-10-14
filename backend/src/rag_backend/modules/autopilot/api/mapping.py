"""Map the HTTP topic batch to and from the intake use case."""

from __future__ import annotations

from rag_backend.modules.autopilot.api.schemas import (
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


def command_from(batch: TopicBatch) -> TopicIntakeCommand:
    """Copy validated proposals into the use-case command."""
    proposals = tuple(_input(item) for item in batch.topics)
    return TopicIntakeCommand(proposals=proposals)


def response_from(result: TopicIntakeResult) -> TopicIntakeResponse:
    """Copy the use-case result into the HTTP body."""
    rejected = [
        RejectedTopic(title=item.title, reason=item.reason) for item in result.rejected
    ]
    return TopicIntakeResponse(
        accepted=list(result.accepted),
        queued=list(result.queued),
        rejected=rejected,
    )


def _input(item: TopicProposal) -> ProposalInput:
    return ProposalInput(
        title=item.title,
        angle=item.angle,
        why_viral=item.why_viral,
        audience=item.audience,
        niche=item.niche,
        brief=item.brief,
        sources=tuple(item.sources),
        score=item.score,
        image_style=item.image_style.value,
        image_guidance=item.image_guidance,
    )
