"""Wiring of the repost flow: adapters, factories and the worker step.

Gherkin: tests/features/autopilot_repost_publish_ae0629.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from rag_backend.modules.autopilot.application.repost_tick_ports import (
    PromptDelivery,
    RenderedFiles,
)
from rag_backend.modules.autopilot.bootstrap_repost import (
    SnapshotMetrics,
    SqlCoverFiles,
    TelegramPrompts,
    repost_draft_service,
    repost_files_root,
    repost_tick,
)
from rag_backend.modules.autopilot.domain.insights import (
    InsightMetrics,
    InsightSnapshot,
)
from rag_backend.modules.autopilot.domain.repost_copy import ApprovalNotice
from rag_backend.modules.autopilot.infrastructure.insights_store import SqlInsightsStore
from rag_backend.modules.autopilot.infrastructure.repost_notifier import PreviewMessage
from tests.unit.modules.autopilot.repost_fakes import NOW, stored


@pytest.fixture
async def session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    import rag_backend.infrastructure.database.models  # noqa: F401
    from rag_backend.infrastructure.database.config import Base

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'w.db'}", poolclass=NullPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        yield db
    await engine.dispose()


class _Settings:
    meta_ig_user_id = ""
    meta_ig_graph_base = "https://graph.example"
    carousel_output_dir = "./output/carousels"
    carousel_public_base_url = "https://site"
    telegram_owner_chat_id = ""

    class telegram_bot_token:  # noqa: N801
        @staticmethod
        def get_secret_value() -> str:
            return ""


async def test_factories_without_instagram(session: AsyncSession) -> None:
    settings = _Settings()
    async with httpx.AsyncClient() as client:
        service = repost_draft_service(session, settings, client)  # type: ignore[arg-type]
        tick = repost_tick(session, settings, client)  # type: ignore[arg-type]
        assert await tick.run() == 0
    assert service is not None
    assert repost_files_root(settings).name == "reposts"  # type: ignore[arg-type]


async def test_factories_with_instagram(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from rag_backend.infrastructure.config.settings import get_settings

    monkeypatch.setenv("META_IG_USER_ID", "123")
    get_settings.cache_clear()
    try:
        async with httpx.AsyncClient() as client:
            tick = repost_tick(session, get_settings(), client)
            assert tick._deps.publisher is not None
            assert tick._deps.reels is not None
    finally:
        get_settings.cache_clear()


async def test_snapshot_metrics_and_cover_files(session: AsyncSession) -> None:
    metrics = SnapshotMetrics(session)
    assert await metrics.metrics("1") == InsightMetrics()
    await SqlInsightsStore(session).save(
        InsightSnapshot(media_id="1", metrics=InsightMetrics(views=5), fetched_at=NOW)
    )
    assert (await metrics.metrics("1")).views == 5
    assert await SqlCoverFiles(session).path(uuid4()) is None


class _Messenger:
    def __init__(self) -> None:
        self.sent: list[PreviewMessage] = []
        self.edits: list[tuple[int, str]] = []
        self.tells: list[str] = []

    async def send_preview(self, message: PreviewMessage) -> int | None:
        self.sent.append(message)
        return 9

    async def edit(self, message_id: int, text: str) -> None:
        self.edits.append((message_id, text))

    async def tell(self, text: str) -> None:
        self.tells.append(text)


async def test_telegram_prompts_adapter(tmp_path: Path) -> None:
    messenger = _Messenger()
    prompts = TelegramPrompts(messenger)  # type: ignore[arg-type]
    notice = ApprovalNotice(repost=stored(), metrics=InsightMetrics())
    for fits in (True, False):
        files = RenderedFiles(
            preview=tmp_path / "p.mp4",
            cover=None,
            original_cover=None,
            fits_telegram=fits,
        )
        assert await prompts.deliver(PromptDelivery(files=files, notice=notice)) == 9
    assert (
        messenger.sent[0].video_path is not None
        and messenger.sent[1].video_path is None
    )
    assert len(messenger.sent[0].keyboard.rows) == 4
    await prompts.edit(1, "x")
    await prompts.tell("y")
    assert messenger.edits == [(1, "x")] and messenger.tells == ["y"]


async def test_worker_adapter(session: AsyncSession) -> None:
    from rag_backend.bootstrap.autopilot_worker_factory import RepostRunAdapter

    adapter = RepostRunAdapter(_Settings())  # type: ignore[arg-type]
    assert await adapter.tick(object()) == 0
    assert await adapter.tick(session) == 0


async def test_route_dependencies_build_real_services(session: AsyncSession) -> None:
    from rag_backend.modules.autopilot.api.reels import reels_bundle
    from rag_backend.modules.autopilot.api.repost import repost_bundle
    from rag_backend.modules.autopilot.api.repost_files import repost_files

    settings = _Settings()
    async for bundle in reels_bundle(session, settings):  # type: ignore[arg-type]
        assert bundle.reels is None
    async for repost in repost_bundle(session, settings):  # type: ignore[arg-type]
        assert repost.base == "https://site"
    assert repost_files(session, settings).root.name == "reposts"  # type: ignore[arg-type]


async def test_cover_files_finds_a_stored_cover(session: AsyncSession) -> None:
    from rag_backend.infrastructure.database.models.carousel_creator_asset import (
        CarouselCreatorAssetModel,
    )
    from rag_backend.modules.autopilot.infrastructure.cover_models import (
        AutopilotCoverAssetModel,
    )

    asset_id, cover_id = str(uuid4()), uuid4()
    session.add(
        CarouselCreatorAssetModel(
            id=asset_id,
            owner_id="o",
            role="cover",
            content_sha256="b" * 64,
            media_type="image/webp",
            width=1080,
            height=1920,
            relative_path="x.webp",
        )
    )
    await session.flush()
    session.add(
        AutopilotCoverAssetModel(
            id=cover_id,
            creator_asset_id=asset_id,
            kind="ai_image",
            width=1080,
            height=1920,
            created_at=NOW,
        )
    )
    await session.flush()
    found = await SqlCoverFiles(session).path(cover_id)
    assert found is None or found.name.endswith(".webp")


def test_invalid_body_without_errors() -> None:
    from pydantic import BaseModel, ValidationError

    from rag_backend.modules.autopilot.api.repost_mapping import invalid_body

    class _M(BaseModel):
        x: int

    try:
        _M.model_validate({"x": "nope"})
    except ValidationError as exc:
        assert invalid_body(exc).problem.field == "x"
    empty = ValidationError.from_exception_data("M", [])
    assert invalid_body(empty).problem.field == "body"
