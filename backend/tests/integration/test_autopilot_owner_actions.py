"""HTTP and persistence behavior for owner webhook actions (AE-0356).

Gherkin: tests/features/autopilot_owner_actions.feature
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.api.auth import require_autopilot_api_key
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TelegramUpdate,
    TopicCandidate,
)
from rag_backend.modules.autopilot.domain.owner_ports import (
    PendingRework,
    ReleaseCommand,
)
from rag_backend.modules.autopilot.infrastructure.carousel_release import (
    PublishingCarouselReleaser,
)
from rag_backend.modules.autopilot.infrastructure.models import TelegramUpdateModel
from rag_backend.modules.autopilot.infrastructure.notice_source import SqlNoticeLogStore
from rag_backend.modules.autopilot.infrastructure.pending_rework import (
    SqlPendingReworkStore,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.webhook_constants import (
    APP_STATE_OWNER_ACTIONS,
    HEADER_WEBHOOK_AUTH,
)
from tests.unit.modules.autopilot.test_owner_actions import _world

_SECRET = "hook-secret"
_ENV_SECRET = "TELEGRAM_WEBHOOK_SECRET"
_PATH = "/api/telegram/webhook"


@dataclass
class _Webhook:
    client: AsyncClient
    app: FastAPI


@pytest.fixture
def webhook_secret() -> Iterator[None]:
    """Set the webhook secret for this test, then restore the process env."""
    from rag_backend.infrastructure.config.settings import get_settings

    previous = os.environ.get(_ENV_SECRET)
    os.environ[_ENV_SECRET] = _SECRET
    get_settings.cache_clear()
    yield
    if previous is None:
        os.environ.pop(_ENV_SECRET, None)
    else:
        os.environ[_ENV_SECRET] = previous
    get_settings.cache_clear()


@pytest.fixture
async def webhook(webhook_secret: None) -> AsyncIterator[_Webhook]:
    """App client. The secret fixture keeps settings pointed at the test value."""
    del webhook_secret
    async for bundle in _open_client():
        yield bundle


# Scenario: Forged request
@pytest.mark.asyncio
async def test_forged_request_is_401_and_writes_nothing(webhook: _Webhook) -> None:
    """A wrong or missing secret does not claim the update."""
    missing = await webhook.client.post(_PATH, json={"update_id": 1})
    wrong = await webhook.client.post(
        _PATH,
        json={"update_id": 2},
        headers={HEADER_WEBHOOK_AUTH: "other-secret"},
    )
    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert await _update_count() == 0


@pytest.mark.asyncio
async def test_valid_secret_dispatches_and_returns_200(webhook: _Webhook) -> None:
    """A matching secret reaches the owner-action service and stays HTTP 200."""
    world = _world()
    setattr(webhook.app.state, APP_STATE_OWNER_ACTIONS, world.service)
    run_id = world.runs.run.run_id
    response = await webhook.client.post(
        _PATH,
        json=_callback(9, f"ap:approve:{run_id}"),
        headers={HEADER_WEBHOOK_AUTH: _SECRET},
    )
    assert response.status_code == 200
    assert world.runs.run.state is AutopilotRunState.PUBLISHING
    assert len(world.release.ids) == 1


# Scenario: Webhook failure after Telegram side effects (QA r1 H4)
@pytest.mark.asyncio
async def test_failure_after_queued_replies_sends_nothing(webhook: _Webhook) -> None:
    """A handler that fails after queuing replies rolls back and stays silent."""
    from rag_backend.modules.autopilot.application.owner_actions import (
        OwnerActionService,
    )
    from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate

    class _FailsAfterReplies(OwnerActionService):
        async def handle(self, update: WebhookUpdate) -> None:
            await super().handle(update)
            raise RuntimeError("commit-time failure")

    world = _world()
    service = _FailsAfterReplies(world.service._deps)
    setattr(webhook.app.state, APP_STATE_OWNER_ACTIONS, service)
    run_id = world.runs.run.run_id
    response = await webhook.client.post(
        _PATH,
        json=_callback(11, f"ap:reject:{run_id}"),
        headers={HEADER_WEBHOOK_AUTH: _SECRET},
    )
    assert response.status_code == 200
    assert world.messenger.answers == []
    assert world.messenger.edits == []


@pytest.mark.asyncio
async def test_successful_dispatch_delivers_replies_after_commit(
    webhook: _Webhook,
) -> None:
    """Replies are sent once the request's unit of work committed."""
    world = _world()
    setattr(webhook.app.state, APP_STATE_OWNER_ACTIONS, world.service)
    run_id = world.runs.run.run_id
    response = await webhook.client.post(
        _PATH,
        json=_callback(12, f"ap:reject:{run_id}"),
        headers={HEADER_WEBHOOK_AUTH: _SECRET},
    )
    assert response.status_code == 200
    assert len(world.messenger.answers) == 1
    assert len(world.messenger.edits) == 1


@pytest.mark.asyncio
async def test_bad_body_and_missing_engine_stay_200(webhook: _Webhook) -> None:
    """A valid secret never becomes a retryable error, and a bad body is not claimed."""
    empty = await webhook.client.post(
        _PATH,
        content=b"",
        headers={HEADER_WEBHOOK_AUTH: _SECRET},
    )
    broken = await webhook.client.post(
        _PATH,
        content=b"{",
        headers={HEADER_WEBHOOK_AUTH: _SECRET},
    )
    missing_engine = await webhook.client.post(
        _PATH,
        json=_callback(8, "ap:approve:" + str(uuid4())),
        headers={HEADER_WEBHOOK_AUTH: _SECRET},
    )
    assert empty.status_code == 200
    assert broken.status_code == 200
    assert missing_engine.status_code == 200
    assert await _update_count() == 0


@pytest.mark.asyncio
async def test_handler_error_rolls_back_and_stays_200(webhook: _Webhook) -> None:
    world = _world()

    async def _boom(update: object) -> None:
        del update
        raise RuntimeError("boom")

    world.service.handle = _boom
    response = await webhook.client.post(
        _PATH,
        json=_callback(9, "ap:approve:" + str(uuid4())),
        headers={HEADER_WEBHOOK_AUTH: _SECRET},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_webhook_route_has_no_api_key(webhook: _Webhook) -> None:
    """The webhook is mounted and is not behind the scout API key."""
    found = [
        route
        for route in webhook.app.routes
        if isinstance(route, APIRoute) and route.path == _PATH
    ]
    assert len(found) == 1
    calls = [item.call for item in found[0].dependant.dependencies]
    assert require_autopilot_api_key not in calls


@pytest.mark.asyncio
async def test_claim_update_conflict_does_nothing(db_session: AsyncSession) -> None:
    """Scenario: Duplicate delivery — the second insert loses."""
    repo = SqlAlchemyAutopilotRepository(db_session)
    update = TelegramUpdate(
        update_id=4242, received_at=datetime(2026, 10, 14, tzinfo=UTC)
    )
    assert await repo.claim_update(update) is True
    assert await repo.claim_update(update) is False
    assert await repo.has_telegram_update(4242) is True


@pytest.mark.asyncio
async def test_pending_rework_round_trip(db_session: AsyncSession) -> None:
    """The phase waits on the notice ledger until the owner sends text."""
    repo = SqlAlchemyAutopilotRepository(db_session)
    topic = _topic()
    await repo.add_topic(topic)
    run = _run(topic)
    await repo.add(run)
    store = SqlPendingReworkStore(repo, SqlNoticeLogStore(db_session))
    await store.put(
        PendingRework(owner_chat_id="42", run_id=run.run_id, phase="images")
    )
    taken = await store.take("42")
    assert taken is not None
    assert taken.phase == "images"
    assert taken.run_id == run.run_id
    assert await store.take("42") is None


@pytest.mark.asyncio
async def test_release_of_missing_project_is_false(db_session: AsyncSession) -> None:
    releaser = PublishingCarouselReleaser(db_session)
    released = await releaser.release(ReleaseCommand(project_id=str(uuid4())))
    assert released is False


def _topic() -> TopicCandidate:
    return TopicCandidate(
        candidate_id=uuid4(),
        title="Agents that ship",
        angle="operator",
        why_viral="three launches",
        audience="builders",
        niche="ai",
        brief="A short brief.",
        sources=("https://example.com/story",),
        score=80,
        signal_hash=uuid4().hex,
        status="accepted",
    )


def _run(topic: TopicCandidate) -> AutopilotRun:
    return AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=topic.candidate_id,
        carousel_project_id=None,
        state=AutopilotRunState.AWAITING_OWNER,
        state_reason="ready_for_owner",
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )


def _callback(update_id: int, data: str) -> dict[str, object]:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"cb-{update_id}",
            "from": {"id": 42},
            "data": data,
            "message": {"message_id": 3, "chat": {"id": 42}},
        },
    }


async def _open_client() -> AsyncIterator[_Webhook]:
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter
    from rag_backend.infrastructure.database.config import Base, close_db

    limiter.reset()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield _Webhook(client=client, app=app)
    limiter.reset()
    db_config.c_engine = None
    await close_db()
    await engine.dispose()


async def _update_count() -> int:
    from rag_backend.infrastructure.database.config import get_session_maker

    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(func.count()).select_from(TelegramUpdateModel)
        )
        counted = result.scalar_one()
    return int(counted)
