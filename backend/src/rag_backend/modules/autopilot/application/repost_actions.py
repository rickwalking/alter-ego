"""Owner buttons on a repost draft: Aprovar, Usar capa original, Editar legenda,
Rejeitar, and the caption the owner types after Editar legenda (ADR-0031).

Only a pending draft whose preview was sent and whose 12 h window is open can
be decided. Every move is a compare-and-set, so a second tap does nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Protocol

import structlog

from rag_backend.modules.autopilot.application.deferred_replies import (
    DeferredOwnerMessenger,
)
from rag_backend.modules.autopilot.application.owner_replies import OwnerReplies
from rag_backend.modules.autopilot.application.repost_tick_ports import (
    OriginalMetrics,
)
from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.domain.owner_ports import MessageEdit
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.recommend import ScheduleSignals
from rag_backend.modules.autopilot.domain.repost import (
    Repost,
    RepostCallback,
    RepostError,
    parse_repost_callback,
)
from rag_backend.modules.autopilot.domain.repost_copy import (
    ApprovalNotice,
    approval_keyboard,
    approval_text,
    approved_text,
)
from rag_backend.modules.autopilot.domain.repost_ports import (
    RepostStore,
    StatusChange,
)
from rag_backend.modules.autopilot.domain.repost_rules import check_caption
from rag_backend.modules.autopilot.domain.repost_schedule import (
    PublishTimeQuery,
    publish_time,
)
from rag_backend.modules.autopilot.domain.schedule_ports import ScheduleSignalsSource
from rag_backend.modules.autopilot.domain.topic_text import strip_controls
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.repost_constants import (
    ACTOR_OWNER_PREFIX,
    ANSWER_APPROVED,
    ANSWER_CAPTION,
    ANSWER_GONE,
    ANSWER_REJECTED,
    CALLBACK_CAPTION,
    CALLBACK_NO,
    CALLBACK_ORIGINAL,
    CAPTION_EDIT_TTL_MINUTES,
    COVER_ORIGINAL,
    LOG_DECIDED,
    LOG_REPOST,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    TEXT_CAPTION_INVALID,
    TEXT_CAPTION_PROMPT,
    TEXT_DECIDED_REJECTED,
)
from rag_backend.modules.autopilot.webhook_constants import ANSWER_UNKNOWN

logger = structlog.get_logger()


class _Deps(Protocol):
    """The owner-action collaborators a repost decision reads."""

    @property
    def clock(self) -> Clock: ...

    @property
    def owner_chat_id(self) -> str: ...

    @property
    def reposts(self) -> RepostStore | None: ...

    @property
    def repost_metrics(self) -> OriginalMetrics | None: ...

    @property
    def schedule_signals(self) -> ScheduleSignalsSource | None: ...


class _Host(Protocol):
    """The ``OwnerActionService`` attributes the mixin uses."""

    @property
    def _out(self) -> OwnerReplies: ...

    @property
    def _replies(self) -> DeferredOwnerMessenger: ...

    @property
    def _deps(self) -> _Deps: ...


@dataclass(frozen=True, kw_only=True)
class _Tap:
    update: WebhookUpdate
    parsed: RepostCallback
    repost: Repost
    store: RepostStore
    now: datetime


class RepostOwnerActions:
    """Mixin for ``OwnerActionService``."""

    async def _repost_callback(self: _Host, update: WebhookUpdate) -> bool:
        """True when the button belonged to a repost draft."""
        parsed = parse_repost_callback(update.data)
        if parsed is None:
            return False
        store = self._deps.reposts
        if store is None:
            await self._out.answer(update, ANSWER_UNKNOWN)
            return True
        now = self._deps.clock.now()
        repost = await store.get(parsed.repost_id)
        if repost is None or not decidable(repost, now):
            await self._out.answer(update, ANSWER_GONE)
            return True
        tap = _Tap(update=update, parsed=parsed, repost=repost, store=store, now=now)
        await _act(self, tap)
        return True

    async def _repost_caption_reply(self: _Host, update: WebhookUpdate) -> bool:
        """True when the owner's text was the caption a draft was waiting for."""
        store = self._deps.reposts
        if store is None:
            return False
        now = self._deps.clock.now()
        since = now - timedelta(minutes=CAPTION_EDIT_TTL_MINUTES)
        repost = await store.caption_editing(since)
        if repost is None or not decidable(repost, now):
            return False
        caption = strip_controls(update.text).strip()
        try:
            check_caption(caption)
        except RepostError as exc:
            field = exc.message
            await self._out.tell(update, TEXT_CAPTION_INVALID.format(field=field))
            return True
        edited = replace(repost, caption=caption, caption_edit_at=None, updated_at=now)
        if await _moved(store, repost, edited):
            await _refresh_prompt(self, edited)
        return True


def decidable(repost: Repost, now: datetime) -> bool:
    """Pending, previewed, and inside its approval window."""
    if repost.status != STATUS_PENDING or repost.preview_ready_at is None:
        return False
    return now < repost.expires_at


async def _act(host: _Host, tap: _Tap) -> None:
    action = tap.parsed.action
    if action == CALLBACK_CAPTION:
        await _ask_caption(host, tap)
        return
    if action == CALLBACK_NO:
        await _reject(host, tap)
        return
    await _approve(host, tap)


async def _approve(host: _Host, tap: _Tap) -> None:
    repost = tap.repost
    cover = COVER_ORIGINAL if tap.parsed.action == CALLBACK_ORIGINAL else None
    signals = await _signals(host._deps.schedule_signals)
    approved = replace(
        repost,
        status=STATUS_APPROVED,
        cover_choice=cover or repost.default_cover,
        approved_at=tap.now,
        decided_by=f"{ACTOR_OWNER_PREFIX}{tap.update.actor_id}",
        publish_at=publish_time(
            PublishTimeQuery(window=repost.window, now=tap.now, signals=signals)
        ),
        caption_edit_at=None,
        updated_at=tap.now,
    )
    if not await _moved(tap.store, repost, approved):
        await host._out.answer(tap.update, ANSWER_GONE)
        return
    logger.info(LOG_REPOST, outcome=LOG_DECIDED, status=STATUS_APPROVED)
    await host._out.finish(tap.update, ANSWER_APPROVED, approved_text(approved))


async def _reject(host: _Host, tap: _Tap) -> None:
    rejected = replace(
        tap.repost,
        status=STATUS_REJECTED,
        decided_by=f"{ACTOR_OWNER_PREFIX}{tap.update.actor_id}",
        caption_edit_at=None,
        updated_at=tap.now,
    )
    if not await _moved(tap.store, tap.repost, rejected):
        await host._out.answer(tap.update, ANSWER_GONE)
        return
    logger.info(LOG_REPOST, outcome=LOG_DECIDED, status=STATUS_REJECTED)
    await host._out.finish(tap.update, ANSWER_REJECTED, TEXT_DECIDED_REJECTED)


async def _ask_caption(host: _Host, tap: _Tap) -> None:
    asked = replace(tap.repost, caption_edit_at=tap.now, updated_at=tap.now)
    if not await _moved(tap.store, tap.repost, asked):
        await host._out.answer(tap.update, ANSWER_GONE)
        return
    await host._out.answer(tap.update, ANSWER_CAPTION)
    await host._out.ask(tap.update, TEXT_CAPTION_PROMPT)


async def _refresh_prompt(host: _Host, repost: Repost) -> None:
    message_id = repost.telegram_message_id
    chat_id = host._deps.owner_chat_id
    if message_id is None or not chat_id:
        return
    metrics = InsightMetrics()
    if host._deps.repost_metrics is not None:
        metrics = await host._deps.repost_metrics.metrics(repost.media_id)
    text = approval_text(ApprovalNotice(repost=repost, metrics=metrics))
    await host._replies.edit(
        MessageEdit(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            keyboard=approval_keyboard(repost),
        )
    )


async def _moved(store: RepostStore, before: Repost, after: Repost) -> bool:
    return await store.save(StatusChange(expected=before.status, repost=after))


async def _signals(source: ScheduleSignalsSource | None) -> ScheduleSignals:
    if source is None:
        return ScheduleSignals()
    return await source.load()


__all__ = ["RepostOwnerActions", "decidable"]
