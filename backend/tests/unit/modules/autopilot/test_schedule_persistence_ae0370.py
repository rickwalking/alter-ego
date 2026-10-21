"""``scheduled_at`` persistence, the due query, and the reply keyboard.

Gherkin: tests/features/autopilot_scheduled_publish.feature
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.owner_ports import OwnerText
from rag_backend.modules.autopilot.domain.schedule_keyboards import (
    scheduled_keyboard,
)
from rag_backend.modules.autopilot.domain.schedule_ports import DueScheduleQuery
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.infrastructure.schedule_store import (
    SqlScheduledRuns,
)
from rag_backend.modules.autopilot.infrastructure.telegram_reply import (
    ReplyClientConfig,
    TelegramOwnerMessenger,
)
from rag_backend.modules.autopilot.schedule_constants import (
    REASON_OWNER_SCHEDULED,
    REASON_OWNER_UNSCHEDULED,
    REASON_SCHEDULE_DUE,
)

_S = AutopilotRunState
_AT = datetime(2026, 10, 15, 21, 0, tzinfo=UTC)


async def _run(session: AsyncSession, state: AutopilotRunState) -> UUID:
    project_id = str(uuid.uuid4())
    session.add(CarouselProjectModel(id=project_id, topic="t", audience="a", niche="n"))
    await session.flush()
    repo = SqlAlchemyAutopilotRepository(session)
    topic = TopicCandidate(
        candidate_id=uuid4(),
        title="t",
        angle="a",
        why_viral="w",
        audience="a",
        niche="n",
        brief="b",
        sources=(),
        score=80,
        signal_hash=uuid4().hex,
        status="queued",
    )
    await repo.add_topic(topic)
    run = AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=topic.candidate_id,
        carousel_project_id=project_id,
        state=state,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )
    await repo.add(run)
    await session.commit()
    return run.run_id


async def _move(
    repo: SqlAlchemyAutopilotRepository,
    run_id: UUID,
    pair: tuple[AutopilotRunState, AutopilotRunState],
    reason: str,
) -> bool:
    return await repo.transition(
        TransitionCommand(
            run_id=run_id,
            expected=pair[0],
            new=pair[1],
            reason=reason,
            scheduled_at=_AT if pair[1] is _S.SCHEDULED else None,
        )
    )


@pytest.mark.unit
class TestScheduledAtColumn:
    """Entering ``scheduled`` stores the time; cancel clears it; due keeps it."""

    async def test_schedule_then_cancel(self, db_session: AsyncSession) -> None:
        run_id = await _run(db_session, _S.AWAITING_OWNER)
        repo = SqlAlchemyAutopilotRepository(db_session)
        assert await _move(
            repo, run_id, (_S.AWAITING_OWNER, _S.SCHEDULED), REASON_OWNER_SCHEDULED
        )
        stored = await repo.get(run_id)
        assert stored is not None
        assert stored.state is _S.SCHEDULED
        assert stored.scheduled_at == _AT
        assert await _move(
            repo, run_id, (_S.SCHEDULED, _S.AWAITING_OWNER), REASON_OWNER_UNSCHEDULED
        )
        cancelled = await repo.get(run_id)
        assert cancelled is not None
        assert cancelled.scheduled_at is None

    async def test_due_tick_keeps_the_time(self, db_session: AsyncSession) -> None:
        run_id = await _run(db_session, _S.AWAITING_OWNER)
        repo = SqlAlchemyAutopilotRepository(db_session)
        await _move(
            repo, run_id, (_S.AWAITING_OWNER, _S.SCHEDULED), REASON_OWNER_SCHEDULED
        )
        assert await _move(
            repo, run_id, (_S.SCHEDULED, _S.PUBLISHING), REASON_SCHEDULE_DUE
        )
        published = await repo.get(run_id)
        assert published is not None
        assert published.state is _S.PUBLISHING
        assert published.scheduled_at == _AT
        assert published.publish_attempts == 0

    async def test_double_schedule_is_one_cas(self, db_session: AsyncSession) -> None:
        run_id = await _run(db_session, _S.AWAITING_OWNER)
        repo = SqlAlchemyAutopilotRepository(db_session)
        pair = (_S.AWAITING_OWNER, _S.SCHEDULED)
        assert await _move(repo, run_id, pair, REASON_OWNER_SCHEDULED)
        assert not await _move(repo, run_id, pair, REASON_OWNER_SCHEDULED)


@pytest.mark.unit
class TestDueQuery:
    """Only ``scheduled`` runs at or before ``now``, earliest first."""

    async def test_due_runs(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyAutopilotRepository(db_session)
        due_id = await _run(db_session, _S.AWAITING_OWNER)
        await _move(
            repo, due_id, (_S.AWAITING_OWNER, _S.SCHEDULED), REASON_OWNER_SCHEDULED
        )
        other_id = await _run(db_session, _S.AWAITING_OWNER)
        await db_session.commit()
        source = SqlScheduledRuns(db_session)

        early = await source.due(
            DueScheduleQuery(now=_AT - timedelta(seconds=1), limit=5)
        )
        on_time = await source.due(DueScheduleQuery(now=_AT, limit=5))
        capped = await source.due(DueScheduleQuery(now=_AT, limit=0))

        assert early == []
        assert [run.run_id for run in on_time] == [due_id]
        assert on_time[0].scheduled_at == _AT
        assert other_id not in {run.run_id for run in on_time}
        assert capped == []


@pytest.mark.unit
async def test_tell_sends_the_inline_keyboard() -> None:
    """A typed time is confirmed in a new message with the cancel buttons."""
    sent: list[dict[str, object]] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    messenger = TelegramOwnerMessenger(ReplyClientConfig(token="t", client=client))
    run_id = uuid4()
    await messenger.tell(
        OwnerText(chat_id="42", text="ok", keyboard=scheduled_keyboard(run_id))
    )
    await messenger.tell(OwnerText(chat_id="42", text="plain"))
    await client.aclose()

    markup = sent[0]["reply_markup"]
    assert isinstance(markup, dict)
    buttons = markup["inline_keyboard"][1]
    assert buttons[0]["callback_data"] == f"ap:unsched:{run_id}"
    assert "reply_markup" not in sent[1]


@pytest.mark.unit
def test_default_publish_setting() -> None:
    """``AUTOPILOT_DEFAULT_PUBLISH`` defaults to ``now`` and accepts ``next_slot``."""
    assert Settings().autopilot_default_publish == "now"
    assert Settings(
        AUTOPILOT_DEFAULT_PUBLISH="next_slot"
    ).autopilot_default_publish == ("next_slot")
