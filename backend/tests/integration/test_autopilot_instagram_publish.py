"""Persistence for the Instagram publish checkpoint and owner notice.

Gherkin: tests/features/autopilot_instagram_publish.feature
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.modules.autopilot.constants import (
    CALLBACK_RETRY_PREFIX,
    EVENT_TYPE_PUBLISH_NOTICE,
    NOTICE_PUBLISH_FAILED,
    PAYLOAD_ERROR_CODE,
    PAYLOAD_OFFER_RETRY,
    PAYLOAD_RETRY_CALLBACK,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.publish import (
    PublishAttemptCommand,
    PublishNotice,
    SaveContainerCommand,
    SavePostCommand,
)
from rag_backend.modules.autopilot.infrastructure.publish_notifier import (
    OutboxPublishNotifier,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from tests.integration.test_autopilot_state_machine import _persist

_AT = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)


async def _publishing(
    db: AsyncSession,
) -> tuple[SqlAlchemyAutopilotRepository, AutopilotRun]:
    repo = SqlAlchemyAutopilotRepository(db)
    run = await _persist(repo, AutopilotRunState.PUBLISHING)
    return repo, run


@pytest.mark.asyncio
async def test_container_post_and_attempt_round_trip(db_session: AsyncSession) -> None:
    """A stored container survives a later read, and a null permalink does not clear it."""
    repo, run = await _publishing(db_session)

    saved = await repo.save_container(
        SaveContainerCommand(
            run_id=run.run_id, container_id="container-1", created_at=_AT
        )
    )
    posted = await repo.save_post(
        SavePostCommand(run_id=run.run_id, ig_post_id="post-1", ig_permalink=None)
    )
    linked = await repo.save_post(
        SavePostCommand(
            run_id=run.run_id,
            ig_post_id="post-1",
            ig_permalink="https://instagram.com/p/abc",
        )
    )
    kept = await repo.save_post(
        SavePostCommand(run_id=run.run_id, ig_post_id="post-1", ig_permalink=None)
    )
    attempted = await repo.record_attempt(
        PublishAttemptCommand(run_id=run.run_id, attempts=1, reason="503", at=_AT)
    )

    stored = await repo.get(run.run_id)
    assert saved is True
    assert posted is True
    assert linked is True
    assert kept is True
    assert attempted is True
    assert stored is not None
    assert stored.ig_container_id == "container-1"
    assert stored.ig_container_created_at == _AT
    assert stored.ig_post_id == "post-1"
    assert stored.ig_permalink == "https://instagram.com/p/abc"
    assert stored.publish_attempts == 1


@pytest.mark.asyncio
async def test_publish_notice_is_an_outbox_event(db_session: AsyncSession) -> None:
    """Scenario: Permanent Meta error — the owner notice is durable, not a Telegram call."""
    _repo, run = await _publishing(db_session)
    notice = PublishNotice(
        run_id=run.run_id,
        outcome=NOTICE_PUBLISH_FAILED,
        permalink=None,
        error_code="36003",
        offer_retry=True,
    )

    await OutboxPublishNotifier(db_session).notify(notice)

    result = await db_session.execute(
        select(EventOutboxModel).where(EventOutboxModel.aggregate_id == str(run.run_id))
    )
    rows = [
        row
        for row in result.scalars().all()
        if row.event_type == EVENT_TYPE_PUBLISH_NOTICE
    ]
    assert len(rows) == 1
    assert rows[0].payload[PAYLOAD_ERROR_CODE] == "36003"
    assert rows[0].payload[PAYLOAD_OFFER_RETRY] is True
    assert (
        rows[0].payload[PAYLOAD_RETRY_CALLBACK]
        == f"{CALLBACK_RETRY_PREFIX}{run.run_id}"
    )


@pytest.mark.asyncio
async def test_status_is_unpublished_without_a_run(db_session: AsyncSession) -> None:
    """No autopilot run means the carousel has not been handed to Instagram."""
    from rag_backend.modules.autopilot import AutopilotBootstrapDeps, bootstrap_module

    view = await bootstrap_module(
        AutopilotBootstrapDeps(session=db_session)
    ).instagram_status(str(uuid4()))
    assert view.state == "unpublished"
    assert view.ig_post_id is None
    assert view.permalink is None
    assert view.error is None


@pytest.mark.asyncio
async def test_carousel_source_builds_slide_urls(db_session: AsyncSession) -> None:
    """The worker reads workflow, visibility, and public slide URLs from publishing."""
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
        CarouselSlideModel,
    )
    from rag_backend.modules.autopilot.infrastructure.carousel_source import (
        PublishingCarouselSource,
    )
    from rag_backend.modules.publishing import load_instagram_publish_target

    project_id = str(uuid4())
    db_session.add(
        CarouselProjectModel(
            id=project_id,
            topic="T",
            audience="A",
            niche="N",
            caption="hello",
            is_public=True,
            status="completed",
            workflow_status="approved_for_publish",
        )
    )
    db_session.add(
        CarouselSlideModel(
            project_id=project_id,
            slide_number=2,
            slide_type="content",
            heading="H",
            body="B",
        )
    )
    db_session.add(
        CarouselSlideModel(
            project_id=project_id,
            slide_number=1,
            slide_type="intro",
            heading="H",
            body="B",
        )
    )
    await db_session.flush()

    missing = await load_instagram_publish_target(db_session, str(uuid4()))
    assert missing is None
    target = await load_instagram_publish_target(db_session, project_id)
    assert target is not None
    assert target.slide_numbers == (1, 2)
    assert target.caption == "hello"

    source = PublishingCarouselSource(db_session, "https://public.test/")
    snapshot = await source.load(project_id)
    assert snapshot is not None
    assert snapshot.is_public is True
    assert snapshot.image_urls[0].endswith("/slide_1.jpg")
    assert snapshot.image_urls[1].endswith("/slide_2.jpg")
    blank = PublishingCarouselSource(db_session, "")
    without_base = await blank.load(project_id)
    assert without_base is not None
    assert without_base.image_urls == ()
    assert without_base.base_url_configured is False
