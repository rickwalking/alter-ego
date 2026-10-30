"""Owner Approve, Reject and Stop for a boost callback."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.application.boost_requests import (
    BoostDeps,
    BoostRequestService,
    DecideCommand,
)
from rag_backend.modules.autopilot.boost_constants import (
    ACTOR_OWNER_PREFIX,
    CALLBACK_OK,
    CALLBACK_STOP,
    STATUS_ACTIVE,
    STATUS_STOPPED,
)
from rag_backend.modules.autopilot.domain.boost import (
    BoostStore,
    CampaignPauser,
    StatusSave,
    parse_boost_callback,
)
from rag_backend.modules.autopilot.domain.boost_policy import BoostLimits
from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.domain.owner_ports import (
    CallbackAnswer,
    MessageEdit,
    OwnerMessenger,
)
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.webhook_constants import ANSWER_UNKNOWN


class _Deps(Protocol):
    boosts: BoostStore | None
    boost_limits: BoostLimits | None
    pauser: CampaignPauser | None
    messenger: OwnerMessenger
    clock: Clock
    owner_chat_id: str


class _Host(Protocol):
    _deps: _Deps

    async def _answer(self, update: WebhookUpdate, text: str) -> None: ...


class _WebhookMessenger:
    """Adapts the owner messenger so a decision can edit the prompt."""

    def __init__(self, messenger: OwnerMessenger, chat_id: str) -> None:
        self._messenger = messenger
        self._chat_id = chat_id

    async def send(self, text: str, keyboard: InlineKeyboard) -> int | None:
        del text, keyboard
        if self._chat_id == "":
            return None
        return None

    async def edit(self, message_id: int, text: str) -> None:
        await self._messenger.edit(
            MessageEdit(
                chat_id=self._chat_id,
                message_id=message_id,
                text=text,
                keyboard=None,
            )
        )


class BoostOwnerActions:
    """Mixin. True when the callback belonged to a boost request."""

    async def _boost_callback(self: _Host, update: WebhookUpdate) -> bool:
        parsed = parse_boost_callback(update.data)
        if parsed is None:
            return False
        if self._deps.boosts is None or self._deps.boost_limits is None:
            await self._answer(update, ANSWER_UNKNOWN)
            return True
        if parsed.action == CALLBACK_STOP:
            await _stop(self._deps, parsed.request_id)
            await self._answer(update, CALLBACK_STOP)
            return True
        await _decide(
            self._deps,
            _Decision(
                request_id=parsed.request_id,
                action=parsed.action,
                actor_id=update.actor_id,
            ),
        )
        await self._deps.messenger.answer(
            CallbackAnswer(callback_id=update.callback_id, text=parsed.action)
        )
        return True


async def _decide(deps: _Deps, decision: _Decision) -> None:
    limits = deps.boost_limits
    store = deps.boosts
    if limits is None or store is None:
        return
    service = BoostRequestService(
        BoostDeps(
            store=store,
            messenger=_WebhookMessenger(deps.messenger, deps.owner_chat_id),
            clock=deps.clock,
            owner_chat_id=deps.owner_chat_id,
        )
    )
    await service.decide(
        DecideCommand(
            request_id=decision.request_id,
            approve=decision.action == CALLBACK_OK,
            actor=f"{ACTOR_OWNER_PREFIX}{decision.actor_id}",
            limits=limits,
        )
    )


async def _stop(deps: _Deps, request_id: UUID) -> None:
    store = deps.boosts
    if store is None:
        return
    current = await store.get(request_id)
    if current is None or current.status != STATUS_ACTIVE:
        return
    if not await _paused(deps, current.meta_campaign_id):
        return
    updated = replace(current, status=STATUS_STOPPED, decided_at=deps.clock.now())
    await store.save_status(
        StatusSave(previous=STATUS_ACTIVE, request=updated, actor=ACTOR_OWNER_PREFIX)
    )
    await store.commit()


async def _paused(deps: _Deps, campaign_id: str | None) -> bool:
    if campaign_id is None:
        return True
    if deps.pauser is None:
        return False
    return await deps.pauser.pause(campaign_id)


@dataclass(frozen=True, kw_only=True)
class _Decision:
    request_id: UUID
    action: str
    actor_id: str


__all__ = ["BoostOwnerActions"]
