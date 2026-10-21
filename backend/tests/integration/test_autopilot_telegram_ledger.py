"""Notice ledger persistence and on-disk slide lookup.

Gherkin: tests/features/autopilot_telegram_notify.feature
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.modules.autopilot.bootstrap import notifier_is_configured
from rag_backend.modules.autopilot.bootstrap_telegram import (
    TelegramTickConfig,
    build_telegram_notify_tick,
)
from rag_backend.modules.autopilot.constants import (
    AGGREGATE_TYPE_AUTOPILOT_RUN,
    EVENT_TYPE_READY_FOR_OWNER,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
)
from rag_backend.modules.autopilot.domain.notice_log import (
    NoticeLog,
    ReviewRecord,
    record_review,
)
from rag_backend.modules.autopilot.domain.notify import SaveNoticeLog
from rag_backend.modules.autopilot.infrastructure.notice_source import (
    SqlAutopilotEventSource,
    SqlNoticeLogStore,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.infrastructure.review_facts import (
    CarouselReviewFacts,
)


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


@pytest.mark.asyncio
async def test_notice_log_round_trips_without_moving_updated_at(
    db_session: AsyncSession,
) -> None:
    """Scenario: Duplicate event is ignored — the revision is stored."""
    repo = SqlAlchemyAutopilotRepository(db_session)
    topic = _topic()
    await repo.add_topic(topic)
    run = AutopilotRun(
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
        updated_at=datetime(2026, 10, 12, tzinfo=UTC),
    )
    await repo.add(run)
    before = await repo.get(run.run_id)
    assert before is not None
    log = record_review(
        NoticeLog(),
        ReviewRecord(revision=4, album_ids=(10, 11), keyboard_id=12),
    )
    await SqlNoticeLogStore(db_session).save(SaveNoticeLog(run_id=run.run_id, log=log))
    stored = await repo.get(run.run_id)
    assert stored is not None
    assert stored.notice_log.reviews[0].keyboard_id == 12
    assert stored.telegram_message_ids == (10, 11, 12)
    assert stored.updated_at == before.updated_at


@pytest.mark.asyncio
async def test_review_facts_read_pt_slides_from_disk(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Scenario: Owner receives slides and buttons."""
    project_id = str(uuid4())
    language = tmp_path / "pt"
    language.mkdir()
    (language / "slide_1.jpg").write_bytes(b"jpeg")
    (language / "slide_2.jpg").write_bytes(b"jpeg")
    db_session.add(
        CarouselProjectModel(
            id=project_id,
            topic="Agents",
            audience="builders",
            niche="ai",
            caption="hello from the caption",
            output_dir=str(tmp_path),
            is_public=False,
            status="draft",
            workflow_status="draft",
        )
    )
    await db_session.flush()
    facts = await CarouselReviewFacts(db_session).load(project_id)
    assert facts is not None
    assert facts.title == "Agents"
    assert facts.caption == "hello from the caption"
    assert len(facts.slide_paths) == 2
    assert await CarouselReviewFacts(db_session).load("missing") is None
    blank_id = str(uuid4())
    db_session.add(
        CarouselProjectModel(
            id=blank_id,
            topic="Agents",
            audience="builders",
            niche="ai",
            caption=None,
            output_dir=None,
            is_public=False,
            status="draft",
            workflow_status="draft",
        )
    )
    await db_session.flush()
    blank = await CarouselReviewFacts(db_session).load(blank_id)
    assert blank is not None
    assert blank.caption == ""
    assert blank.slide_paths == ()


@pytest.mark.asyncio
async def test_recent_events_skip_bad_ids_and_non_object_payloads(
    db_session: AsyncSession,
) -> None:
    """Events come oldest first, so a busy outbox never hides an older notice."""
    run_id = uuid4()
    db_session.add_all([
        _outbox(str(run_id), {"revision": 4}, datetime(2026, 10, 13, 11, 0)),
        _outbox("not-a-uuid", {"revision": 1}, datetime(2026, 10, 13, 12, 0)),
        _outbox(str(run_id), ["nope"], datetime(2026, 10, 13, 10, 0)),
    ])
    await db_session.flush()
    events = await SqlAutopilotEventSource(db_session).recent()
    mine = [event for event in events if event.run_id == run_id]
    assert len(mine) == 2
    assert mine[0].payload == {}
    assert mine[1].payload == {"revision": 4}
    assert mine[0].created_at.tzinfo is not None
    await SqlNoticeLogStore(db_session).save(
        SaveNoticeLog(run_id=uuid4(), log=NoticeLog())
    )


@pytest.mark.asyncio
async def test_unconfigured_tick_does_not_call_telegram(
    db_session: AsyncSession,
) -> None:
    assert notifier_is_configured(" token ", "") is False
    assert notifier_is_configured("token", "42") is True
    tick = build_telegram_notify_tick(
        TelegramTickConfig(token="", chat_id="", web_base_url="")
    )
    assert await tick.tick(db_session) == 0


def _outbox(
    aggregate_id: str, payload: object, created_at: datetime
) -> EventOutboxModel:
    return EventOutboxModel(
        id=str(uuid4()),
        event_id=str(uuid4()),
        event_type=EVENT_TYPE_READY_FOR_OWNER,
        aggregate_id=aggregate_id,
        aggregate_type=AGGREGATE_TYPE_AUTOPILOT_RUN,
        version=1,
        payload=payload,
        event_timestamp=created_at.isoformat(),
        created_at=created_at,
    )
