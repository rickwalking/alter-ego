"""Map the Grok Bot HTTP bodies to and from the scout use cases."""

from __future__ import annotations

from rag_backend.modules.autopilot.api.schemas import (
    ObservedXPost,
    RejectedXPost,
    XSignalsBatch,
    XSignalsResponse,
)
from rag_backend.modules.autopilot.application.scout_failure import ScoutFailureCommand
from rag_backend.modules.autopilot.application.x_signals import (
    XSignalsCommand,
    XSignalsResult,
)
from rag_backend.modules.autopilot.domain.x_observation import ObservedPostInput


def x_signals_command(batch: XSignalsBatch) -> XSignalsCommand:
    """Copy validated observations into the use-case command."""
    posts = tuple(_post(item) for item in batch.posts)
    return XSignalsCommand(posts=posts)


def x_signals_response(result: XSignalsResult) -> XSignalsResponse:
    """Copy the use-case result into the HTTP body."""
    rejected = [
        RejectedXPost(url=item.url, reason=item.reason) for item in result.rejected
    ]
    return XSignalsResponse(accepted=list(result.accepted), rejected=rejected)


def scout_command(reason: str) -> ScoutFailureCommand:
    """Copy the failure reason into the use-case command."""
    return ScoutFailureCommand(reason=reason)


def _post(item: ObservedXPost) -> ObservedPostInput:
    return ObservedPostInput(
        url=item.url,
        handle=item.handle,
        text=item.text,
        likes=item.likes,
        reposts=item.reposts,
        replies=item.replies,
        views=item.views,
        observed_at=item.observed_at,
    )
