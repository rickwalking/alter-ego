"""Schedule from Telegram, then the due tick publishes, on the real engine.

Gherkin: tests/features/autopilot_scheduled_publish.feature
(Scenario: Schedule, then the due tick, on the real engine)

Real: ``EditorialWorkflowService`` with its LangGraph checkpointer, the run
wrapper and the image phase (the hero image harness), the editorial driver, the
autopilot repository on a file SQLite database, the pending store, the
carousel release and publish source, the due sweep and the publish job. Fake:
the LLM artifacts, the image vendor, the slide render, Graph, the Story step,
and Telegram.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.carousel import (
    editorial_finalize,
)
from rag_backend.application.services.carousel import (
    editorial_workflow_resume_runner as resume_runner,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
)
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.application.owner_actions import (
    OwnerActionDeps,
    OwnerActionService,
)
from rag_backend.modules.autopilot.application.publish_job import (
    InstagramPublishJob,
    PublishJobDependencies,
)
from rag_backend.modules.autopilot.application.scheduled_publish import (
    ScheduledPublishDependencies,
    ScheduledPublishSweep,
)
from rag_backend.modules.autopilot.constants import GATE_FINAL_REVIEW
from rag_backend.modules.autopilot.domain.gate import GateAction
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
)
from rag_backend.modules.autopilot.domain.publish import PostExtras
from rag_backend.modules.autopilot.domain.schedule import epoch_of
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.infrastructure.carousel_release import (
    PublishingCarouselReleaser,
)
from rag_backend.modules.autopilot.infrastructure.carousel_source import (
    PublishingCarouselSource,
)
from rag_backend.modules.autopilot.infrastructure.notice_source import SqlNoticeLogStore
from rag_backend.modules.autopilot.infrastructure.pending_rework import (
    SqlPendingReworkStore,
)
from rag_backend.modules.autopilot.infrastructure.publish_claims import (
    SqlPublishClaims,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.infrastructure.run_recovery_store import (
    SqlRunRecoveryStore,
)
from rag_backend.modules.autopilot.infrastructure.schedule_store import (
    SqlScheduledRuns,
)
from rag_backend.modules.autopilot.webhook_constants import KIND_CALLBACK
from rag_backend.modules.editorial.public import WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
from tests.integration.test_autopilot_hero_images import (
    _drive_to_owner,
    _driver,
    _fake_artifacts,
    _ImageVendor,
    _seed_outline_gate,
    _set_output_dir,
    _World,
)
from tests.unit.modules.autopilot.test_instagram_publish_job import (
    _Gateway,
    _Notifier,
)
from tests.unit.modules.autopilot.test_owner_actions import _Messenger

_SP = ZoneInfo("America/Sao_Paulo")
_OWNER_CHAT = "42"
_BASE_URL = "https://public.test"
_NOW = datetime(2026, 10, 15, 10, 0, tzinfo=_SP).astimezone(UTC)
_SLOT = datetime(2026, 10, 15, 18, 0, tzinfo=_SP).astimezone(UTC)
_CAPTION = "Agents that ship: the carousel caption."


@dataclass
class _Clock:
    at: datetime = _NOW

    def now(self) -> datetime:
        return self.at


@dataclass
class _Story:
    calls: list[str] = field(default_factory=list)

    async def run(self, project_id: str) -> PostExtras:
        self.calls.append(project_id)
        return PostExtras(
            story_status="published", story_error=None, music_style="lo-fi beats"
        )


@pytest_asyncio.fixture
async def world(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[_World]:
    """The hero image harness, driven to final review."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ae0370.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    previous = db_config.c_engine
    db_config.c_engine = engine
    vendor = _ImageVendor()

    async def _finished(project_id: str, reason: str, **_kwargs: object) -> None:
        del project_id, reason

    async def _stage_beat(project_id: str, epoch: int) -> bool:
        del project_id, epoch
        return True

    async def _finalize(db: AsyncSession, project_id: str) -> None:
        del db, project_id

    monkeypatch.setattr(PhaseArtifactRunner, "ensure_for_phase", _fake_artifacts)
    monkeypatch.setattr(resume_runner, "publish_run_finished", _finished)
    monkeypatch.setattr(resume_runner, "write_run_heartbeat_once", _stage_beat)
    monkeypatch.setattr(
        editorial_finalize, "finalize_carousel_after_images_approval", _finalize
    )
    service = EditorialWorkflowService(
        EditorialWorkflowConfig(
            llm=MagicMock(),
            checkpointer=MemorySaver(),
            image_registry=ImageProviderRegistry(vendor, vendor),
        )
    )
    try:
        async with db_config.get_session_maker()() as session:
            driver = _driver(session, service)
            project_id = await _seed_outline_gate(session, service, driver)
            await _set_output_dir(project_id, tmp_path / "carousel")
            built = _World(
                session=session,
                driver=driver,
                vendor=vendor,
                project_id=project_id,
                finalized=[],
            )
            seen = await _drive_to_owner(built)
            assert seen[-1][0].phase == GATE_FINAL_REVIEW
            assert seen[-1][1].action is GateAction.STOP
            yield built
    finally:
        db_config.c_engine = previous
        await engine.dispose()


async def _awaiting_run(world: _World) -> AutopilotRun:
    """The carousel is marked completed and given its caption by hand because in prod
    the (faked) slide render and distribution pack do it.
    """
    repo = SqlAlchemyAutopilotRepository(world.session)
    topic = TopicCandidate(
        candidate_id=uuid4(),
        title="Agents that ship",
        angle="a",
        why_viral="w",
        audience="builders",
        niche="ai",
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
        carousel_project_id=world.project_id,
        state=AutopilotRunState.AWAITING_OWNER,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )
    await repo.add(run)
    await world.session.execute(
        update(CarouselProjectModel)
        .where(CarouselProjectModel.id == world.project_id)
        .values(status="completed", caption=_CAPTION)
    )
    await world.session.commit()
    return run


def _owner_service(world: _World, clock: _Clock) -> OwnerActionService:
    session = world.session
    repo = SqlAlchemyAutopilotRepository(session)
    return OwnerActionService(
        OwnerActionDeps(
            runs=repo,
            updates=repo,
            pending=SqlPendingReworkStore(repo, SqlNoticeLogStore(session)),
            editorial=world.driver,
            release=PublishingCarouselReleaser(session),
            messenger=_Messenger(),
            recovery=SqlRunRecoveryStore(session),
            clock=clock,
            owner_chat_id=_OWNER_CHAT,
            carousels=PublishingCarouselSource(session, _BASE_URL),
        )
    )


def _sweep(world: _World, clock: _Clock) -> ScheduledPublishSweep:
    session = world.session
    repo = SqlAlchemyAutopilotRepository(session)
    return ScheduledPublishSweep(
        ScheduledPublishDependencies(
            runs=repo,
            scheduled=SqlScheduledRuns(session),
            source=PublishingCarouselSource(session, _BASE_URL),
            release=PublishingCarouselReleaser(session),
            notifier=_Notifier(),
            checkpoint=repo,
            clock=clock,
        )
    )


@dataclass
class _Publisher:
    gateway: _Gateway
    notifier: _Notifier
    story: _Story
    job: InstagramPublishJob


def _publisher(world: _World, clock: _Clock) -> _Publisher:
    session = world.session
    repo = SqlAlchemyAutopilotRepository(session)
    gateway, notifier, story = _Gateway(), _Notifier(), _Story()
    job = InstagramPublishJob(
        PublishJobDependencies(
            runs=repo,
            source=PublishingCarouselSource(session, _BASE_URL),
            gateway=gateway,
            notifier=notifier,
            clock=clock,
            checkpoint=repo,
            claims=SqlPublishClaims(session),
            story=story,
        )
    )
    return _Publisher(gateway=gateway, notifier=notifier, story=story, job=job)


async def _project(world: _World) -> CarouselProjectModel:
    result = await world.session.execute(
        select(CarouselProjectModel)
        .where(CarouselProjectModel.id == world.project_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def _tap_slot(
    world: _World, service: OwnerActionService, run: AutopilotRun
) -> None:
    update_ = WebhookUpdate(
        update_id=7001,
        kind=KIND_CALLBACK,
        actor_id=_OWNER_CHAT,
        chat_id=_OWNER_CHAT,
        callback_id="cb-1",
        data=f"ap:at:{epoch_of(_SLOT)}:{run.run_id}",
        message_id=9,
    )
    await service.handle(update_)
    await world.session.commit()
    await service.deliver()


@pytest.mark.asyncio
async def test_schedule_then_due_tick_publishes_with_story(world: _World) -> None:
    clock = _Clock()
    run = await _awaiting_run(world)
    repo = SqlAlchemyAutopilotRepository(world.session)

    await _tap_slot(world, _owner_service(world, clock), run)

    scheduled = await repo.get(run.run_id)
    assert scheduled is not None
    assert scheduled.state is AutopilotRunState.SCHEDULED
    assert scheduled.scheduled_at == _SLOT
    project = await _project(world)
    assert project.workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
    assert project.is_public is False

    clock.at = _SLOT - timedelta(minutes=1)
    assert await _sweep(world, clock).tick() == 0

    clock.at = _SLOT + timedelta(minutes=25)
    assert await _sweep(world, clock).tick() == 1
    assert (await _project(world)).is_public is True
    publisher = _publisher(world, clock)
    assert await publisher.job.tick() == 1

    published = await repo.get(run.run_id)
    assert published is not None
    assert published.state is AutopilotRunState.PUBLISHED
    assert published.ig_post_id == "post-1"
    assert publisher.story.calls == [world.project_id]
    extras = publisher.notifier.notices[-1].extras
    assert extras is not None
    assert extras.story_status == "published"
    assert extras.late_minutes == 25

    assert await _sweep(world, clock).tick() == 0
    assert await publisher.job.tick() == 0
    assert publisher.gateway.opens == 1
