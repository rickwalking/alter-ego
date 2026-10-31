"""The boost request store on real Postgres, where the event foreign key is enforced."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from rag_backend.modules.autopilot.application.boost_requests import (
    BoostDeps,
    BoostRequestService,
    CreateCommand,
    Created,
    DecideCommand,
)
from rag_backend.modules.autopilot.boost_constants import (
    HTTP_ACCEPTED,
    STATUS_APPROVED,
    STATUS_PENDING,
)
from rag_backend.modules.autopilot.domain.boost import BoostAudience, BoostDraft
from rag_backend.modules.autopilot.domain.boost_policy import BoostLimits
from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.infrastructure.boost_models import (
    BoostEventModel,
    BoostRequestModel,
)
from rag_backend.modules.autopilot.infrastructure.boost_store import SqlBoostStore
from rag_backend.modules.autopilot.infrastructure.insights_models import IgMediaModel
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_MEDIA = "18034567890123456"
_TABLES = ("ig_media", "boost_requests", "boost_request_events")
_OWNER = "owner:1"


class _Clock:
    """Wall clock, so the request is inside its approval window."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class _Messenger:
    """Counts owner notices; never calls Telegram."""

    def __init__(self) -> None:
        self.sent = 0

    async def send(self, text: str, keyboard: InlineKeyboard) -> int | None:
        del text, keyboard
        self.sent += 1
        return 7

    async def edit(self, message_id: int, text: str) -> None:
        del message_id, text


def _limits() -> BoostLimits:
    return BoostLimits(
        requests_enabled=True,
        spend_enabled=False,
        max_daily_cents=3000,
        min_daily_cents=600,
        max_days=7,
        max_week_cents=10000,
        max_pending=3,
        max_age_days=30,
        allowed_countries=frozenset({"BR"}),
        approval_ttl_hours=12,
        currency="BRL",
        poll_minutes=60,
        max_attempts=5,
    )


def _draft() -> BoostDraft:
    return BoostDraft(
        media_id=_MEDIA,
        daily_budget_cents=2000,
        days=1,
        objective="engagement",
        audience=BoostAudience(countries=("BR",), age_min=18, age_max=65),
        reason="Alcance acima da mediana da conta",
        score=1.6,
        start_at=None,
        idempotency_key="media-20261031",
    )


@asynccontextmanager
async def _boost_schema() -> AsyncIterator[AsyncEngine]:
    """The boost tables plus one eligible post, in a fresh Postgres schema."""
    async with isolated_schema(_TABLES) as engine:
        async with AsyncSession(engine) as session:
            now = datetime.now(UTC)
            session.add(
                IgMediaModel(
                    media_id=_MEDIA,
                    media_type="CAROUSEL_ALBUM",
                    media_product_type="FEED",
                    posted_at=now - timedelta(days=1),
                    listed_at=now,
                )
            )
            await session.commit()
        yield engine


def _service(session: AsyncSession, messenger: _Messenger) -> BoostRequestService:
    return BoostRequestService(
        BoostDeps(
            store=SqlBoostStore(session),
            messenger=messenger,
            clock=_Clock(),
            owner_chat_id="1",
        )
    )


async def _create(engine: AsyncEngine, messenger: _Messenger) -> Created:
    async with AsyncSession(engine) as session:
        return await _service(session, messenger).create(
            CreateCommand(draft=_draft(), limits=_limits())
        )


async def _counts(engine: AsyncEngine) -> tuple[int, list[tuple[str, str]]]:
    async with AsyncSession(engine) as session:
        rows = await session.scalar(select(func.count()).select_from(BoostRequestModel))
        events = await session.execute(
            select(BoostEventModel.from_status, BoostEventModel.to_status).order_by(
                BoostEventModel.id
            )
        )
        return int(rows or 0), [(str(a), str(b)) for a, b in events]


@requires_postgres
async def test_a_request_is_stored_with_its_first_event() -> None:
    """Scenario: A boost request is stored with its first event on Postgres"""
    async with _boost_schema() as engine:
        messenger = _Messenger()
        created = await _create(engine, messenger)
        rows, events = await _counts(engine)

    assert created.status == HTTP_ACCEPTED
    assert created.request.status == STATUS_PENDING
    assert messenger.sent == 1
    assert rows == 1
    assert [to for _, to in events] == [STATUS_PENDING]


@requires_postgres
async def test_the_owner_approval_is_stored_with_its_event() -> None:
    """Scenario: The owner approval is stored with its event on Postgres"""
    async with _boost_schema() as engine:
        created = await _create(engine, _Messenger())
        async with AsyncSession(engine) as session:
            decided = await _service(session, _Messenger()).decide(
                DecideCommand(
                    request_id=created.request.id,
                    approve=True,
                    actor=_OWNER,
                    limits=_limits(),
                )
            )
        rows, events = await _counts(engine)

    assert decided.status == STATUS_APPROVED
    assert rows == 1
    assert events[-1] == (STATUS_PENDING, STATUS_APPROVED)
    assert len(events) == 2


@requires_postgres
async def test_the_same_key_replays_without_a_second_row() -> None:
    """Scenario: The same idempotency key replays the stored request on Postgres"""
    async with _boost_schema() as engine:
        first = await _create(engine, _Messenger())
        messenger = _Messenger()
        again = await _create(engine, messenger)
        rows, events = await _counts(engine)

    assert again.request.id == first.request.id
    assert messenger.sent == 0
    assert rows == 1
    assert len(events) == 1
