"""Owner taps on "Usar capa do Grok" / back to the default (ADR-0024).

A mixin for ``OwnerActionService`` (same entry point, owner allowlist and
deferred replies as the thesis buttons). Owner-only and idempotent:

- at the thesis (``awaiting_thesis``): the choice is stored on the run
  (compare-and-set on the state) and the prompt's keyboard flips; the carousel
  is then created with the chosen slide 1;
- at the review (``awaiting_owner``): the run moves to ``reworking`` with the
  ``owner_cover`` rework queued; the worker tick re-renders slide 1 and the
  normal final-review stop sends the fresh review;
- a tap for the choice already in place, a run in any other state, or a topic
  without a usable cover changes nothing.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.application.owner_steps import (
    COVER_STEP,
    OwnerStep,
)
from rag_backend.modules.autopilot.cover_constants import (
    ANSWER_COVER_NOT_NOW,
    ANSWER_COVER_OFF,
    ANSWER_COVER_ON,
    ANSWER_COVER_SAME,
    COVER_REWORK_PHASE,
    TEXT_COVER_SWITCHING,
)
from rag_backend.modules.autopilot.domain.cover_offer import (
    CoverCallback,
    CoverOffer,
    chosen_as,
    parse_cover_callback,
)
from rag_backend.modules.autopilot.domain.cover_ports import (
    CoverChoiceCommand,
    CoverChoiceStore,
    CoverOffers,
)
from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
)
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    TopicCandidateRepository,
)
from rag_backend.modules.autopilot.domain.recovery import ReworkIntent, RunRecoveryStore
from rag_backend.modules.autopilot.domain.thesis import (
    thesis_keyboard,
    thesis_prompt_text,
)
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate


class _CoverDeps(Protocol):
    @property
    def runs(self) -> AutopilotRunRepository: ...

    @property
    def recovery(self) -> RunRecoveryStore: ...

    @property
    def topics(self) -> TopicCandidateRepository | None: ...

    @property
    def covers(self) -> CoverOffers | None: ...

    @property
    def cover_choices(self) -> CoverChoiceStore | None: ...


class _Host(Protocol):
    """What the mixin needs from ``OwnerActionService``."""

    @property
    def _deps(self) -> _CoverDeps: ...

    async def _answer(self, update: WebhookUpdate, text: str) -> None: ...

    async def _edit(
        self, update: WebhookUpdate, text: str, keyboard: InlineKeyboard | None
    ) -> None: ...

    async def _finish(self, update: WebhookUpdate, answer: str, text: str) -> None: ...

    async def _apply(self, run_id: UUID, step: OwnerStep) -> bool: ...


class CoverOwnerActions:
    """Switch slide 1 to the GrokBot cover, or back to the default."""

    async def _cover_callback(self: _Host, update: WebhookUpdate) -> bool:
        """Handle a cover button. False when ``update`` is not one."""
        parsed = parse_cover_callback(update.data)
        if parsed is None:
            return False
        found = await _offered(self, parsed)
        if found is None:
            await self._answer(update, ANSWER_COVER_NOT_NOW)
            return True
        run, offer = found
        if run.cover_chosen == parsed.use_cover:
            await self._answer(update, ANSWER_COVER_SAME)
            return True
        await _route(self, update, (run, offer, parsed))
        return True


async def _route(
    host: _Host,
    update: WebhookUpdate,
    target: tuple[AutopilotRun, CoverOffer, CoverCallback],
) -> None:
    """The thesis prompt, the review, or "not now" for any other state."""
    run, offer, parsed = target
    if run.state is AutopilotRunState.AWAITING_THESIS:
        await _at_thesis(host, update, (run, chosen_as(offer, chosen=parsed.use_cover)))
        return
    if run.state is AutopilotRunState.AWAITING_OWNER and run.carousel_project_id:
        await _at_review(host, update, (run, parsed))
        return
    await host._answer(update, ANSWER_COVER_NOT_NOW)


async def _offered(
    host: _Host, parsed: CoverCallback
) -> tuple[AutopilotRun, CoverOffer] | None:
    covers = host._deps.covers
    if covers is None or host._deps.cover_choices is None:
        return None
    run = await host._deps.runs.get(parsed.run_id)
    if run is None:
        return None
    offer = await covers.offer(run)
    if offer is None:
        return None
    return run, offer


def _answer_for(*, use_cover: bool) -> str:
    return ANSWER_COVER_ON if use_cover else ANSWER_COVER_OFF


async def _store_choice(host: _Host, command: CoverChoiceCommand) -> bool:
    choices = host._deps.cover_choices
    return choices is not None and await choices.set_cover_choice(command)


async def _at_thesis(
    host: _Host, update: WebhookUpdate, target: tuple[AutopilotRun, CoverOffer]
) -> None:
    """Store the choice and flip the thesis prompt's keyboard."""
    run, offer = target
    stored = await _store_choice(
        host,
        CoverChoiceCommand(
            run_id=run.run_id,
            expected=AutopilotRunState.AWAITING_THESIS,
            chosen=offer.chosen,
        ),
    )
    topics = host._deps.topics
    topic = await topics.get_topic(run.topic_candidate_id) if topics else None
    if not stored or topic is None:
        await host._answer(update, ANSWER_COVER_NOT_NOW)
        return
    await host._answer(update, _answer_for(use_cover=offer.chosen))
    await host._edit(
        update, thesis_prompt_text(topic), thesis_keyboard(run.run_id, offer)
    )


async def _at_review(
    host: _Host, update: WebhookUpdate, target: tuple[AutopilotRun, CoverCallback]
) -> None:
    """Queue the slide-1 re-render; the worker tick applies it."""
    run, parsed = target
    if not await host._apply(run.run_id, COVER_STEP):
        await host._answer(update, ANSWER_COVER_NOT_NOW)
        return
    await _store_choice(
        host,
        CoverChoiceCommand(
            run_id=run.run_id,
            expected=AutopilotRunState.REWORKING,
            chosen=parsed.use_cover,
        ),
    )
    await host._deps.recovery.queue_rework(
        ReworkIntent(run_id=run.run_id, phase=COVER_REWORK_PHASE, feedback="")
    )
    await host._finish(
        update, _answer_for(use_cover=parsed.use_cover), TEXT_COVER_SWITCHING
    )


__all__ = ["CoverOwnerActions"]
