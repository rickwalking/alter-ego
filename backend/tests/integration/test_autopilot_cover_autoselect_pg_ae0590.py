"""The autopilot cover auto-selection through the real stack, on Postgres.

Feature: Use the autopilot's generated cover on slide 1
(tests/features/autopilot_cover_autoselect_ae0590.feature). The autostart
helper, the generation service and runner, the asset store, the cover switch
(project lock + lock-version CAS) and the repository are real; only the image
bridge is a fake editor and the background task is run inline. Skipped
without a Postgres ``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverSelection,
    AutoCoverWrite,
    CoverBaseline,
)
from rag_backend.domain.constants.cover_autoselect import (
    LOG_COVER_AUTO_SELECT,
    OUTCOME_AUTO_SELECT_ALREADY,
    REASON_AUTO_SELECT_ASSET_GONE,
    REASON_AUTO_SELECT_CONFLICT,
    REASON_AUTO_SELECT_MANUAL_CHOICE,
    REASON_AUTO_SELECT_NO_PROJECT,
)
from rag_backend.domain.constants.creator_asset import build_creator_asset_filename
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database import config as db_config
from rag_backend.infrastructure.database.models import UserModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.carousel_creator_asset import (
    CarouselCreatorAssetModel,
)
from rag_backend.modules.editorial.infrastructure import carousel_cover_autostart
from rag_backend.modules.editorial.infrastructure.carousel_cover_autoselect import (
    EditorialAutoCoverStore,
    auto_cover_selector,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_autostart import (
    schedule_autopilot_cover,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_lock import (
    carousel_project_lock,
)
from rag_backend.modules.editorial.public import CoverRunWiring
from tests.integration.cover_generation_support import FakeEditor, cover_png
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.test_autopilot_cover_autostart_pg_ae0581 import _tables

Task = Callable[[], Awaitable[object]]


@dataclass
class _Harness:
    """The isolated engine, the fake bridge and the captured background task."""

    engine: AsyncEngine
    editor: FakeEditor
    tasks: list[Task] = field(default_factory=list)


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "out"))
    get_settings.cache_clear()
    yield assets
    get_settings.cache_clear()


def _no_publish(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Any republish, finalize or Instagram call is recorded (and must not happen)."""
    calls: list[str] = []
    from rag_backend.application.services.carousel import carousel_republish
    from rag_backend.modules.autopilot.infrastructure import instagram_gateway
    from rag_backend.modules.editorial.infrastructure import carousel_owner_autofix

    def _record(name: str) -> Callable[..., Awaitable[object]]:
        async def _call(*_args: object, **_kwargs: object) -> object:
            calls.append(name)
            raise AssertionError(name)

        return _call

    monkeypatch.setattr(
        carousel_owner_autofix.RepublishRenderer, "render", _record("render")
    )
    monkeypatch.setattr(
        carousel_republish,
        "finalize_carousel_after_images_approval",
        _record("finalize"),
    )
    for gateway in ("SteppedInstagramGateway", "AtomicInstagramGateway"):
        cls = getattr(instagram_gateway, gateway)
        monkeypatch.setattr(cls, "open_carousel", _record("open_carousel"))
        monkeypatch.setattr(cls, "publish_atomic", _record("publish_atomic"))
    return calls


def _harness(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> _Harness:
    """Fake bridge, inline background task, sessions on the isolated engine."""
    harness = _Harness(engine=engine, editor=FakeEditor())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db_config, "get_session_maker", lambda: factory)
    monkeypatch.setattr(
        carousel_cover_autostart,
        "cover_run_wiring",
        lambda _render: CoverRunWiring(
            editor=harness.editor,
            render_prompt=lambda text: text,
            now=lambda: datetime.now(UTC),
        ),
    )
    from rag_backend.application.services.carousel import cover_generation_tasks

    monkeypatch.setattr(
        cover_generation_tasks,
        "schedule_cover_generation",
        lambda task, _gid: harness.tasks.append(task),
    )
    return harness


async def _seed(engine: AsyncEngine, assets: Path) -> tuple[str, list[str]]:
    """A POV carousel paused at the content gate and two library photos."""
    owner_id, project_id = str(uuid4()), str(uuid4())
    photo_ids = [str(uuid4()), str(uuid4())]
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add(
            UserModel(
                id=owner_id,
                email=f"{owner_id}@pg.test",
                full_name="Owner",
                hashed_password="x",
                role="editor",
            )
        )
        await session.flush()
        for photo_id in photo_ids:
            digest = hashlib.sha256(photo_id.encode()).hexdigest()
            session.add(
                CarouselCreatorAssetModel(
                    id=photo_id,
                    owner_id=owner_id,
                    content_sha256=digest,
                    media_type="image/webp",
                    width=1080,
                    height=1350,
                    relative_path=f"{owner_id}/{digest}.webp",
                    role="hook",
                )
            )
            (assets / build_creator_asset_filename(digest)).write_bytes(cover_png())
        await session.flush()
        session.add(
            CarouselProjectModel(
                id=project_id,
                topic="Agentes em produção",
                audience="Devs",
                niche="IA",
                owner_id=owner_id,
                content_mode="pov",
                status="drafting",
                current_phase="content",
                phase_status="awaiting_human",
                lock_version=3,
                hook_asset_id=photo_ids[0],
            )
        )
        await session.commit()
    return project_id, photo_ids


async def _row(engine: AsyncEngine, project_id: str) -> CarouselProjectModel:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        return model


async def _start(harness: _Harness, project_id: str) -> Task:
    """Schedule through the real autostart helper; the captured task."""
    factory = async_sessionmaker(harness.engine, expire_on_commit=False)
    async with factory() as session:
        outcome = await schedule_autopilot_cover(session, project_id)
    assert outcome.scheduled, outcome.reason
    assert len(harness.tasks) == 1
    return harness.tasks[0]


async def _result_asset(engine: AsyncEngine, project_id: str) -> str | None:
    from rag_backend.modules.editorial.infrastructure.cover_generations import (
        SqlCoverGenerationRepository,
    )

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        rows = await SqlCoverGenerationRepository(session).for_project(project_id)
    assert len(rows) == 1
    found = rows[0].result_asset_id
    return str(found) if found else None


@requires_postgres
@pytest.mark.asyncio
async def test_succeeded_cover_becomes_slide_one_without_publishing(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The generated cover is stored under the CAS, with no render or publish."""
    # Scenario: A succeeded autopilot cover becomes slide 1's cover
    # Scenario: The selection never re-renders or publishes
    calls = _no_publish(monkeypatch)
    async with isolated_schema(_tables()) as engine:
        project_id, photos = await _seed(engine, dirs)
        harness = _harness(engine, monkeypatch)

        await (await _start(harness, project_id))()

        asset = await _result_asset(engine, project_id)
        row = await _row(engine, project_id)
        assert asset is not None
        assert isinstance(row.slide_cover, dict)
        assert row.slide_cover["asset_id"] == asset
        assert row.slide_cover["kind"] == "ai_image"
        assert row.lock_version == 4
        assert row.status == "drafting"
        assert row.hook_asset_id == photos[0]
        assert row.is_public is False
        assert calls == []


@requires_postgres
@pytest.mark.asyncio
async def test_photo_rebound_while_the_job_ran_is_kept(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A slide-1 photo the owner bound after scheduling is never overridden."""
    # Scenario: A manual choice made while the job ran is kept
    async with isolated_schema(_tables()) as engine:
        project_id, photos = await _seed(engine, dirs)
        harness = _harness(engine, monkeypatch)
        task = await _start(harness, project_id)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            await session.execute(
                update(CarouselProjectModel)
                .where(CarouselProjectModel.id == project_id)
                .values(hook_asset_id=photos[1])
            )
            await session.commit()

        with capture_logs() as logs:
            await task()

        row = await _row(engine, project_id)
        assert await _result_asset(engine, project_id) is not None
        assert row.slide_cover is None
        assert row.hook_asset_id == photos[1]
        assert row.lock_version == 3
        skips = [e for e in logs if e["event"] == LOG_COVER_AUTO_SELECT]
        assert [e["reason"] for e in skips] == [REASON_AUTO_SELECT_MANUAL_CHOICE]


@requires_postgres
@pytest.mark.asyncio
async def test_failed_generation_leaves_slide_one_alone(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bridge failure settles the row failed and never selects."""
    # Scenario: A failed generation leaves slide 1 alone
    async with isolated_schema(_tables()) as engine:
        project_id, photos = await _seed(engine, dirs)
        harness = _harness(engine, monkeypatch)
        harness.editor.error = RuntimeError("grok refused")
        task = await _start(harness, project_id)

        with capture_logs() as logs:
            await task()

        row = await _row(engine, project_id)
        assert await _result_asset(engine, project_id) is None
        assert row.slide_cover is None
        assert row.hook_asset_id == photos[0]
        assert row.lock_version == 3
        assert not [e for e in logs if e["event"] == LOG_COVER_AUTO_SELECT]
        store = EditorialAutoCoverStore(
            async_sessionmaker(engine, expire_on_commit=False)
        )
        failed = await _generation_id(engine, project_id)
        assert await store.result_asset(failed) is None


@requires_postgres
@pytest.mark.asyncio
async def test_held_project_lock_is_a_logged_skip_never_retried(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Another holder of the project lock makes the write a conflict skip."""
    # Scenario: A lock-version conflict is skipped and logged, never retried
    async with isolated_schema(_tables()) as engine:
        project_id, _ = await _seed(engine, dirs)
        harness = _harness(engine, monkeypatch)
        task = await _start(harness, project_id)

        with capture_logs() as logs:
            async with carousel_project_lock(engine, project_id, blocking=False):
                await task()

        row = await _row(engine, project_id)
        assert row.slide_cover is None
        assert row.lock_version == 3
        skips = [e for e in logs if e["event"] == LOG_COVER_AUTO_SELECT]
        assert [e["reason"] for e in skips] == [REASON_AUTO_SELECT_CONFLICT]


@requires_postgres
@pytest.mark.asyncio
async def test_rerun_after_selection_changes_nothing(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second selection for the same generation is a no-op."""
    # Scenario: Selecting the same cover twice changes nothing
    async with isolated_schema(_tables()) as engine:
        project_id, photos = await _seed(engine, dirs)
        harness = _harness(engine, monkeypatch)
        await (await _start(harness, project_id))()
        generation = await _generation_id(engine, project_id)
        selection = AutoCoverSelection(
            project_id=project_id,
            generation_id=generation,
            baseline=CoverBaseline(
                slide_cover_asset_id=None, hook_asset_id=UUID(photos[0])
            ),
        )

        outcome = await auto_cover_selector().select(selection)

        assert outcome == OUTCOME_AUTO_SELECT_ALREADY
        assert (await _row(engine, project_id)).lock_version == 4


@requires_postgres
@pytest.mark.asyncio
async def test_store_refuses_gone_rows_and_assets(dirs: Path) -> None:
    """Unknown generation, project or asset: nothing is written."""
    # Scenario: A generated cover whose file is gone is skipped
    async with isolated_schema(_tables()) as engine:
        project_id, photos = await _seed(engine, dirs)
        store = EditorialAutoCoverStore(
            async_sessionmaker(engine, expire_on_commit=False)
        )
        baseline = CoverBaseline(
            slide_cover_asset_id=None, hook_asset_id=UUID(photos[0])
        )

        def _write(target: str, base: CoverBaseline = baseline) -> AutoCoverWrite:
            return AutoCoverWrite(
                project_id=target,
                asset_id=uuid4(),
                expected_version=3,
                baseline=base,
            )

        assert await store.result_asset(uuid4()) is None
        assert await store.load(str(uuid4())) is None
        loaded = await store.load(project_id)
        assert loaded is not None
        assert loaded.lock_version == 3
        assert await store.write(_write(str(uuid4()))) == REASON_AUTO_SELECT_NO_PROJECT
        assert await store.write(_write(project_id)) == REASON_AUTO_SELECT_ASSET_GONE
        moved = CoverBaseline(slide_cover_asset_id=None, hook_asset_id=uuid4())
        assert (
            await store.write(_write(project_id, moved))
            == REASON_AUTO_SELECT_MANUAL_CHOICE
        )
        row = await _row(engine, project_id)
        assert row.slide_cover is None
        assert row.lock_version == 3


async def _generation_id(engine: AsyncEngine, project_id: str) -> UUID:
    from rag_backend.modules.editorial.infrastructure.cover_generations import (
        SqlCoverGenerationRepository,
    )

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        rows = await SqlCoverGenerationRepository(session).for_project(project_id)
    return rows[0].id
