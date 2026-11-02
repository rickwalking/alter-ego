"""Create and read boost requests. The key cannot approve them."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from rag_backend.modules.autopilot.boost_constants import (
    ACTOR_OWNER_PREFIX,
    ERR_IDEMPOTENCY_REUSED,
    ERR_NOT_FOUND,
    ERR_REASON,
    HTTP_ACCEPTED,
    HTTP_CONFLICT,
    HTTP_NOT_FOUND,
    HTTP_OK,
    HTTP_UNPROCESSABLE,
    REASON_MIN_LENGTH,
    STATUS_APPROVED,
    STATUS_EXPIRED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_REJECTED,
    WEEK_DAYS,
)
from rag_backend.modules.autopilot.domain.boost import (
    BoostDraft,
    BoostError,
    BoostRequest,
    BoostStore,
    StatusSave,
    request_hash,
)
from rag_backend.modules.autopilot.domain.boost_copy import (
    boost_keyboard,
    boost_message,
)
from rag_backend.modules.autopilot.domain.boost_policy import (
    BoostLimits,
    PolicyFacts,
    check_request,
)
from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.topic_text import strip_controls


class BoostMessenger(Protocol):
    """Sends and edits the owner prompt. None when Telegram has no message id."""

    async def send(self, text: str, keyboard: InlineKeyboard) -> int | None:
        """Deliver the prompt. Return the message id when Telegram provides one."""
        ...

    async def edit(self, message_id: int, text: str) -> None:
        """Replace the prompt and drop the buttons."""
        ...


@dataclass(frozen=True, kw_only=True)
class BoostDeps:
    """Store, clock and the owner chat."""

    store: BoostStore
    messenger: BoostMessenger
    clock: Clock
    owner_chat_id: str


@dataclass(frozen=True, kw_only=True)
class CreateCommand:
    """One bot request plus the caps in force."""

    draft: BoostDraft
    limits: BoostLimits


@dataclass(frozen=True, kw_only=True)
class Created:
    """The stored row and the HTTP status (202 new, 200 replay)."""

    request: BoostRequest
    status: int


class BoostRequestService:
    """API-key create and read."""

    def __init__(self, deps: BoostDeps) -> None:
        self._deps = deps

    async def create(self, command: CreateCommand) -> Created:
        """Insert pending_approval or replay the idempotency key."""
        draft = _cleaned(command.draft)
        command = replace(command, draft=draft)
        existing = await self._deps.store.by_key(draft.idempotency_key)
        if existing is not None:
            return _replay(existing, draft)
        now = self._deps.clock.now()
        facts = await _facts(self._deps.store, draft, now)
        check_request(draft, command.limits, facts)
        request = _pending(_Built(command=command, facts=facts, now=now))
        await self._deps.store.insert(request)
        await self._deps.store.commit()
        await _notify(
            self._deps,
            _Notice(
                request=request,
                committed=facts.committed_cents,
                limits=command.limits,
            ),
        )
        return Created(request=request, status=HTTP_ACCEPTED)

    async def get(self, request_id: UUID) -> BoostRequest:
        """The row, or 404."""
        found = await self._deps.store.get(request_id)
        if found is None:
            raise BoostError(ERR_NOT_FOUND, HTTP_NOT_FOUND)
        return found

    async def decide(self, command: DecideCommand) -> BoostRequest:
        """Owner approve or reject. A failed re-check becomes failed."""
        current = await self.get(command.request_id)
        now = self._deps.clock.now()
        move = _Move(current=current, actor=command.actor, now=now)
        if current.status != STATUS_PENDING:
            return current
        if now > current.expires_at:
            return await _move(self._deps, replace(move, status=STATUS_EXPIRED))
        if not command.approve:
            return await _move(self._deps, replace(move, status=STATUS_REJECTED))
        try:
            facts = await _facts_for_request(self._deps.store, current, now)
            check_request(draft_of(current), command.limits, facts)
        except BoostError as exc:
            failed = replace(move, status=STATUS_FAILED, error_code=exc.code)
            return await _move(self._deps, failed)
        return await _move(self._deps, replace(move, status=STATUS_APPROVED))


def _cleaned(draft: BoostDraft) -> BoostDraft:
    reason = strip_controls(draft.reason)
    if len(reason) < REASON_MIN_LENGTH:
        raise BoostError(ERR_REASON, HTTP_UNPROCESSABLE)
    return replace(draft, reason=reason)


def _replay(existing: BoostRequest, draft: BoostDraft) -> Created:
    if existing.request_hash != request_hash(draft):
        raise BoostError(ERR_IDEMPOTENCY_REUSED, HTTP_CONFLICT)
    return Created(request=existing, status=HTTP_OK)


async def _facts(store: BoostStore, draft: BoostDraft, now: datetime) -> PolicyFacts:
    since = now - timedelta(days=WEEK_DAYS)
    return PolicyFacts(
        now=now,
        committed_cents=await store.committed_cents(since),
        pending_count=await store.pending_count(),
        media=await store.media(draft.media_id),
        open_exists=await store.open_exists(draft.media_id),
    )


async def _facts_for_request(
    store: BoostStore, request: BoostRequest, now: datetime
) -> PolicyFacts:
    facts = await _facts(store, draft_of(request), now)
    already = request.total_budget_cents
    return replace(
        facts,
        open_exists=False,
        pending_count=0,
        committed_cents=max(0, facts.committed_cents - already),
    )


def _pending(built: _Built) -> BoostRequest:
    draft = built.command.draft
    limits = built.command.limits
    total = draft.daily_budget_cents * draft.days
    return BoostRequest(
        id=uuid4(),
        idempotency_key=draft.idempotency_key,
        request_hash=request_hash(draft),
        media_id=draft.media_id,
        status=STATUS_PENDING,
        objective=draft.objective,
        daily_budget_cents=draft.daily_budget_cents,
        days=draft.days,
        total_budget_cents=total,
        currency=limits.currency,
        audience=draft.audience,
        reason=draft.reason,
        score=draft.score,
        created_at=built.now,
        expires_at=built.now + timedelta(hours=limits.approval_ttl_hours),
        permalink=built.facts.media.permalink,
        starts_at=draft.start_at,
    )


def draft_of(request: BoostRequest) -> BoostDraft:
    """The stored request as the draft the caps are checked on."""
    return BoostDraft(
        media_id=request.media_id,
        daily_budget_cents=request.daily_budget_cents,
        days=request.days,
        objective=request.objective,
        audience=request.audience,
        reason=request.reason,
        score=request.score,
        start_at=request.starts_at,
        idempotency_key=request.idempotency_key,
    )


async def _notify(deps: BoostDeps, notice: _Notice) -> None:
    request = notice.request
    text = boost_message(
        request,
        notice.committed + request.total_budget_cents,
        notice.limits.max_week_cents,
    )
    message_id = await deps.messenger.send(text, boost_keyboard(request))
    if message_id is None:
        return
    await deps.store.remember_message(request.id, message_id)
    await deps.store.commit()


async def _move(deps: BoostDeps, move: _Move) -> BoostRequest:
    current = move.current
    updated = replace(
        current,
        status=move.status,
        decided_at=move.now,
        decided_by=move.actor.removeprefix(ACTOR_OWNER_PREFIX) or move.actor,
        error_code=move.error_code or current.error_code,
    )
    await deps.store.save_status(
        StatusSave(previous=current.status, request=updated, actor=move.actor)
    )
    if current.telegram_message_id is not None:
        note = f"{move.status} {move.error_code or ''}".strip()
        await deps.messenger.edit(current.telegram_message_id, note)
    await deps.store.commit()
    return updated


@dataclass(frozen=True, kw_only=True)
class DecideCommand:
    """An owner decision."""

    request_id: UUID
    approve: bool
    actor: str
    limits: BoostLimits


@dataclass(frozen=True, kw_only=True)
class _Built:
    command: CreateCommand
    facts: PolicyFacts
    now: datetime


@dataclass(frozen=True, kw_only=True)
class _Notice:
    request: BoostRequest
    committed: int
    limits: BoostLimits


@dataclass(frozen=True, kw_only=True)
class _Move:
    current: BoostRequest
    status: str = ""
    actor: str
    now: datetime
    error_code: str | None = None


__all__ = [
    "BoostDeps",
    "BoostMessenger",
    "BoostRequestService",
    "CreateCommand",
    "Created",
    "DecideCommand",
    "draft_of",
]
