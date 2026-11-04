"""The owner's "Tentar de novo" on an escalated run's carousel (``ap:cr:``).

The tap runs the generation queue's owner Retry on the webhook's session (the
caller commits): it re-drives or revises the carousel's blocked phase and moves
the escalated run back to ``generating`` in one transaction. Owner-only is
enforced twice: ``is_owner`` on the chat before any dispatch, and the Retry
itself compares the carousel's owner with the autopilot owner's user. An
accepted Retry edits the message to "Refazendo a fase …"; a refusal answers
with its own text and leaves the message and its button as they were.
"""

from __future__ import annotations

from typing import Protocol

from rag_backend.modules.autopilot.carousel_retry_constants import (
    ANSWER_CAROUSEL_RETRY,
    ANSWER_CAROUSEL_RETRY_REFUSED,
    TEXT_CAROUSEL_RETRY_ACCEPTED,
)
from rag_backend.modules.autopilot.domain.carousel_retry import (
    CarouselRetrier,
    CarouselRetryRequest,
    parse_carousel_retry,
    refusal_text,
)
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.webhook_constants import ANSWER_ALREADY, TEXT_ALREADY


class _RetryDeps(Protocol):
    @property
    def runs(self) -> AutopilotRunRepository: ...

    @property
    def owner_user_id(self) -> str: ...

    @property
    def carousel_retrier(self) -> CarouselRetrier | None: ...


class _Host(Protocol):
    """What the mixin needs from ``OwnerActionService``."""

    @property
    def _deps(self) -> _RetryDeps: ...

    async def _answer(self, update: WebhookUpdate, text: str) -> None: ...

    async def _finish(self, update: WebhookUpdate, answer: str, text: str) -> None: ...

    async def _tell(self, update: WebhookUpdate, text: str) -> None: ...


class CarouselRetryOwnerActions:
    """Retry the carousel of an escalated run."""

    async def _carousel_retry_callback(self: _Host, update: WebhookUpdate) -> bool:
        """Handle ``ap:cr:<run>``. False when ``update`` is not that button."""
        run_id = parse_carousel_retry(update.data)
        if run_id is None:
            return False
        run = await self._deps.runs.get(run_id)
        retrier = self._deps.carousel_retrier
        if run is None or not run.carousel_project_id or retrier is None:
            await self._finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return True
        outcome = await retrier.retry(
            CarouselRetryRequest(
                project_id=run.carousel_project_id,
                actor_id=self._deps.owner_user_id,
            )
        )
        if outcome.accepted:
            text = TEXT_CAROUSEL_RETRY_ACCEPTED.format(phase=outcome.phase)
            await self._finish(update, ANSWER_CAROUSEL_RETRY, text)
            return True
        await self._answer(update, ANSWER_CAROUSEL_RETRY_REFUSED)
        await self._tell(update, refusal_text(outcome.refusal))
        return True


__all__ = ["CarouselRetryOwnerActions"]
