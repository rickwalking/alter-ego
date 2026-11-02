"""The picker refuses a published carousel, on Postgres.

Feature: tests/features/website_cover_review_switch_ae0594.feature and
tests/features/reopen_review_on_cover_switch_ae0597.feature (wired without a
checkpoint reopen, an approved or scheduled carousel is still refused). The real
picker (``cover_pick_service``: library, generated covers, the cover switch
and the editorial approval read); the render is recorded. Skipped without a
Postgres ``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import update
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.cover_pick import (
    CoverPickCommand,
    CoverPickError,
)
from rag_backend.domain.constants.carousel_autofix import AUTOFIX_STATUS_FIXED
from rag_backend.domain.constants.cover_autoselect import LOG_COVER_AUTO_SELECT
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
    REASON_AUTO_SELECT_APPROVED,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.application.owner_steps import APPROVE_STEP
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.infrastructure.cover_review_hold import (
    SessionCoverReviewHold,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_pick import (
    EditorialCoverLibrary,
)
from rag_backend.modules.editorial.infrastructure.carousel_owner_autofix import (
    RepublishRenderer,
)
from rag_backend.modules.editorial.public import (
    CarouselAutomationAcl,
    CarouselProjectWriteOwner,
    cover_pick_service,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.website_cover_review_pg_support import (
    Harness,
    harness,
    row,
    run_facts,
    seed,
    seed_run,
    tables,
    website_task,
)

_APPROVED = {"workflow_status": "approved_for_publish"}


class _NoOffer:
    async def offer(self, project_id: str) -> SlideCover | None:
        del project_id
        return None


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "out"))
    get_settings.cache_clear()
    yield assets
    get_settings.cache_clear()


class _Checkpoint:
    """Records the checkpoint reopens (no LangGraph thread in these tests)."""

    def __init__(self) -> None:
        self.reopened: list[str] = []

    async def reopen(self, project_id: str) -> bool:
        self.reopened.append(project_id)
        return True


async def _pick(
    built: Harness, project_id: str, photo: str, checkpoint: _Checkpoint | None = None
) -> str:
    """Pick library photo ``photo`` at the seeded lock version."""
    async with built.sessions()() as session:
        project = await CarouselAutomationAcl(session).load_project(project_id)
        assert project is not None
        service = cover_pick_service(session, _NoOffer(), checkpoint)
        result = await service.pick(
            CoverPickCommand(
                project=project,
                asset_id=UUID(photo),
                expected_version=3,
            )
        )
    return result.status


async def _refused(built: Harness, project_id: str, photos: list[str]) -> None:
    with pytest.raises(CoverPickError) as refused:
        await _pick(built, project_id, photos[1])
    assert refused.value.code == ERR_COVER_SWITCH_REQUIRES_REVIEW
    await _unchanged(built, project_id, photos)


async def _refused_by_the_switch(
    built: Harness, project_id: str, photos: list[str]
) -> None:
    """The switch, wired without a checkpoint reopen, refuses under the lock."""
    status = await _pick(built, project_id, photos[1])
    assert status == ERR_COVER_SWITCH_REQUIRES_REVIEW
    await _unchanged(built, project_id, photos)


async def _unchanged(built: Harness, project_id: str, photos: list[str]) -> None:
    model = await row(built, project_id)
    assert model.hook_asset_id == photos[0]
    assert model.slide_cover is None
    assert model.lock_version == 3
    assert built.renders == []


@requires_postgres
@pytest.mark.asyncio
async def test_picker_refuses_an_approved_carousel(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Approved, no checkpoint reopen wired: refused, nothing written or rendered."""
    # Scenario: A switch that cannot reopen the review refuses an approved carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs, **_APPROVED)

        await _refused_by_the_switch(built, project_id, photos)


@requires_postgres
@pytest.mark.asyncio
async def test_picker_refuses_a_scheduled_carousel(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scheduled, no checkpoint reopen wired: refused."""
    # Scenario: A switch that cannot reopen the review refuses an approved carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs, **_APPROVED)
        await seed_run(built, project_id, AutopilotRunState.SCHEDULED)

        await _refused_by_the_switch(built, project_id, photos)


@requires_postgres
@pytest.mark.asyncio
async def test_picker_refuses_a_published_carousel(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Released: refused, the public slides never change."""
    # Scenario: The picker refuses a published carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs, is_public=True)

        await _refused(built, project_id, photos)


@requires_postgres
@pytest.mark.asyncio
async def test_picker_still_switches_a_carousel_in_review(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Waiting for its first approval: the pick switches and re-renders."""
    # Scenario: A carousel waiting for its first approval switches and stays in review
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)

        assert await _pick(built, project_id, photos[1]) == AUTOFIX_STATUS_FIXED

        model = await row(built, project_id)
        assert model.hook_asset_id == photos[1]
        assert model.lock_version == 4
        assert built.renders == [None]


@requires_postgres
@pytest.mark.asyncio
async def test_an_approval_before_the_locked_write_is_dropped(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The picker read a draft; an approval lands first: the locked write sees it
    and drops it with the new slide 1."""
    # Scenario: An approval that lands while the picker switches is dropped with the write
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        original = EditorialCoverLibrary.stage

        async def _approve_then_stage(
            self: EditorialCoverLibrary,
            project: CarouselProject,
            asset: CarouselCreatorAsset,
        ) -> None:
            async with built.sessions()() as other:
                await other.execute(
                    update(CarouselProjectModel)
                    .where(CarouselProjectModel.id == project_id)
                    .values(workflow_status="approved_for_publish")
                )
                await other.commit()
            await original(self, project, asset)

        monkeypatch.setattr(EditorialCoverLibrary, "stage", _approve_then_stage)
        checkpoint = _Checkpoint()

        assert await _pick(built, project_id, photos[1], checkpoint) == (
            AUTOFIX_STATUS_FIXED
        )

        model = await row(built, project_id)
        assert model.hook_asset_id == photos[1]
        assert model.lock_version == 4
        assert model.workflow_status == "draft"
        assert model.phase_status == "awaiting_human"
        assert checkpoint.reopened == [project_id]
        assert built.renders == [None]


@requires_postgres
@pytest.mark.asyncio
async def test_telegram_publish_and_the_review_hold_race(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Publish now and the website hold race on the run row: exactly one wins."""
    # Scenario: A Telegram publish and a website cover switch race
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await seed_run(built, project_id, AutopilotRunState.AWAITING_OWNER)
        facts = await run_facts(built, project_id)
        assert facts is not None
        async with built.sessions()() as session:
            found = await SqlAlchemyAutopilotRepository(session).find_by_carousel(
                project_id
            )
        assert found is not None

        async def _publish_now() -> bool:
            async with built.sessions()() as session:
                repo = SqlAlchemyAutopilotRepository(session)
                moved = await repo.transition(
                    TransitionCommand(
                        run_id=found.run_id,
                        expected=APPROVE_STEP.expected,
                        new=APPROVE_STEP.new,
                        reason=APPROVE_STEP.reason,
                    )
                )
                await session.commit()
                return moved

        held, published = await asyncio.gather(
            SessionCoverReviewHold(built.sessions()).hold(project_id), _publish_now()
        )

        assert (held is not None) != published
        after = await run_facts(built, project_id)
        assert after is not None
        expected = (
            AutopilotRunState.PUBLISHING if published else AutopilotRunState.REWORKING
        )
        assert after.state == expected.value
        if published:
            await _approved_after_publish(built, project_id)
            with capture_logs() as logs:
                await (await website_task(built, project_id, photos[0]))()
            reasons = [
                e.get("reason") for e in logs if e["event"] == LOG_COVER_AUTO_SELECT
            ]
            assert reasons == [REASON_AUTO_SELECT_APPROVED]
            assert (await row(built, project_id)).slide_cover is None


async def _approved_after_publish(built: Harness, project_id: str) -> None:
    """The publish path's approve landed (it bumps the version and approves)."""
    async with built.sessions()() as other:
        await other.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == project_id)
            .values(workflow_status="approved_for_publish", lock_version=4)
        )
        await other.commit()


@requires_postgres
@pytest.mark.asyncio
async def test_a_pick_marks_slide_one_until_its_render_settles(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The marker is set with the pick and cleared only after the render."""
    # Scenario: No approval lands while a cover switch is between write and render
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        during: list[datetime | None] = []

        async def _render(_self: RepublishRenderer, pid: str) -> tuple[str, ...]:
            during.append((await row(built, pid)).needs_republish_since)
            return ()

        monkeypatch.setattr(RepublishRenderer, "render", _render)

        assert await _pick(built, project_id, photos[1]) == AUTOFIX_STATUS_FIXED

        assert during and during[0] is not None
        assert (await row(built, project_id)).needs_republish_since is None


@requires_postgres
@pytest.mark.asyncio
async def test_a_marker_stamped_during_a_render_survives_its_clear(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Compare-and-clear: a newer stamp than the render's start is kept."""
    # Scenario: No approval lands while a cover switch is between write and render
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, _ = await seed(built, dirs)
        rendered_from = datetime.now(UTC)
        async with built.sessions()() as session:
            owner = CarouselProjectWriteOwner(session)
            await owner.mark_needs_republish(project_id)
            await session.commit()
            await owner.clear_needs_republish(project_id, rendered_from)

        assert (await row(built, project_id)).needs_republish_since is not None

        async with built.sessions()() as session:
            await CarouselProjectWriteOwner(session).clear_needs_republish(
                project_id, datetime.now(UTC)
            )
        assert (await row(built, project_id)).needs_republish_since is None
