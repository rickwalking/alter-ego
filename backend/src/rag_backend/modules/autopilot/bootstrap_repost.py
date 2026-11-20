"""Wiring of the repost flow: draft service, worker tick and their adapters."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.repost_drafts import (
    RepostDeps,
    RepostDraftService,
)
from rag_backend.modules.autopilot.application.repost_tick import (
    RepostTick,
    RepostTickDeps,
)
from rag_backend.modules.autopilot.application.repost_tick_ports import (
    PromptDelivery,
)
from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.repost_copy import (
    approval_keyboard,
    approval_text,
)
from rag_backend.modules.autopilot.infrastructure.cover_images import (
    EditorialCoverImages,
)
from rag_backend.modules.autopilot.infrastructure.cover_store import SqlCoverAssetStore
from rag_backend.modules.autopilot.infrastructure.graph_json import (
    GraphJson,
    graph_config,
)
from rag_backend.modules.autopilot.infrastructure.insights_store import SqlInsightsStore
from rag_backend.modules.autopilot.infrastructure.reels_gateway import (
    build_reel_gateway,
)
from rag_backend.modules.autopilot.infrastructure.repost_graph import (
    GraphReelPublisher,
)
from rag_backend.modules.autopilot.infrastructure.repost_notifier import (
    PreviewMessage,
    TelegramRepostMessenger,
)
from rag_backend.modules.autopilot.infrastructure.repost_store import SqlRepostStore
from rag_backend.modules.autopilot.infrastructure.repost_studio import (
    FileRepostStudio,
    StudioConfig,
)
from rag_backend.modules.autopilot.infrastructure.repost_video import (
    FfmpegRenderer,
    FfprobeReelProbe,
    HttpDownloader,
    reposts_dir,
)


class SqlCoverFiles:
    """``CoverFiles`` over the cover rows and the editorial image store."""

    def __init__(self, session: AsyncSession) -> None:
        self._covers = SqlCoverAssetStore(session)
        self._images = EditorialCoverImages(session)

    async def path(self, asset_id: UUID) -> Path | None:
        """The stored WebP of the cover, or None."""
        cover = (await self._covers.covers_by_ids((asset_id,))).get(asset_id)
        if cover is None:
            return None
        found = await self._images.image_file(cover.creator_asset_id)
        return None if found is None else Path(found)


class SnapshotMetrics:
    """``OriginalMetrics`` from the insights snapshot table."""

    def __init__(self, session: AsyncSession) -> None:
        self._store = SqlInsightsStore(session)

    async def metrics(self, media_id: str) -> InsightMetrics:
        """The stored snapshot's metrics, or empty metrics."""
        snapshot = (await self._store.snapshots([media_id])).get(media_id)
        return InsightMetrics() if snapshot is None else snapshot.metrics


class TelegramPrompts:
    """``RepostPrompts`` over the Telegram repost messenger."""

    def __init__(self, messenger: TelegramRepostMessenger) -> None:
        self._messenger = messenger

    async def deliver(self, delivery: PromptDelivery) -> int | None:
        """Cover, preview (when it fits), then the prompt with buttons."""
        files = delivery.files
        return await self._messenger.send_preview(
            PreviewMessage(
                cover_path=files.cover,
                video_path=files.preview if files.fits_telegram else None,
                text=approval_text(delivery.notice),
                keyboard=approval_keyboard(delivery.notice.repost),
            )
        )

    async def edit(self, message_id: int, text: str) -> None:
        """Replace the prompt text."""
        await self._messenger.edit(message_id, text)

    async def tell(self, text: str) -> None:
        """A plain owner message."""
        await self._messenger.tell(text)


def repost_draft_service(
    session: AsyncSession, settings: Settings, client: httpx.AsyncClient
) -> RepostDraftService:
    """The API-key draft service for one request."""
    store = SqlRepostStore(session)
    return RepostDraftService(
        RepostDeps(
            store=store,
            covers=SqlCoverAssetStore(session),
            facts=store,
            reels=build_reel_gateway(settings, client),
            probe=FfprobeReelProbe(),
            clock=SystemClock(),
        )
    )


def repost_tick(
    session: AsyncSession, settings: Settings, client: httpx.AsyncClient
) -> RepostTick:
    """One worker pass on the session."""
    return RepostTick(
        RepostTickDeps(
            store=SqlRepostStore(session),
            studio=_studio(session, settings, client),
            prompts=TelegramPrompts(_messenger(settings)),
            metrics=SnapshotMetrics(session),
            clock=_clock(),
            reels=build_reel_gateway(settings, client),
            publisher=_publisher(settings, client),
        )
    )


def repost_files_root(settings: Settings) -> Path:
    """Where the repost files live."""
    return reposts_dir(settings.carousel_output_dir)


def _studio(
    session: AsyncSession, settings: Settings, client: httpx.AsyncClient
) -> FileRepostStudio:
    return FileRepostStudio(
        StudioConfig(
            root=repost_files_root(settings),
            public_base_url=settings.carousel_public_base_url,
            downloader=HttpDownloader(client),
            renderer=FfmpegRenderer(),
            covers=SqlCoverFiles(session),
        )
    )


def _messenger(settings: Settings) -> TelegramRepostMessenger:
    return TelegramRepostMessenger(
        token=settings.telegram_bot_token.get_secret_value(),
        chat_id=settings.telegram_owner_chat_id,
    )


def _publisher(
    settings: Settings, client: httpx.AsyncClient
) -> GraphReelPublisher | None:
    config = graph_config(settings)
    if config is None:
        return None
    return GraphReelPublisher(GraphJson(config, client))


def _clock() -> Clock:
    return SystemClock()


__all__ = [
    "SnapshotMetrics",
    "SqlCoverFiles",
    "TelegramPrompts",
    "repost_draft_service",
    "repost_files_root",
    "repost_tick",
]
