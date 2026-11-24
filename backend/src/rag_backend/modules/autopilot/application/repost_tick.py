"""One worker pass over repost drafts: render, notify, expire, publish (ADR-0031).

Every transition is a compare-and-set on the status, so a webhook tap racing
the tick never moves a draft twice. A transient Graph error leaves the draft
for the next tick; a permanent one ends it ``failed``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

import structlog

from rag_backend.modules.autopilot.application.repost_tick_ports import (
    ContainerRequest,
    ContainerState,
    OriginalMetrics,
    PromptDelivery,
    ReelPublisher,
    RenderedFiles,
    RepostPrompts,
    RepostRenderError,
    RepostStudio,
    StudioJob,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.repost import Repost
from rag_backend.modules.autopilot.domain.repost_copy import ApprovalNotice
from rag_backend.modules.autopilot.domain.repost_ports import (
    ReelGateway,
    RepostStore,
    StatusChange,
)
from rag_backend.modules.autopilot.repost_constants import (
    CONTAINER_ERROR,
    CONTAINER_EXPIRED,
    CONTAINER_FINISHED,
    CONTAINER_PUBLISHED,
    CONTAINER_TIMEOUT_MINUTES,
    COVER_GROK,
    ERR_CONTAINER_ERROR,
    ERR_CONTAINER_TIMEOUT,
    ERR_PUBLISH_FAILED,
    ERR_SOURCE_UNAVAILABLE,
    FILE_COVER,
    FILE_ORIGINAL_COVER,
    FILE_PREVIEW,
    LOG_EXPIRED,
    LOG_NOTIFIED,
    LOG_NOTIFY_FAILED,
    LOG_PROCESSING,
    LOG_PUBLISH_FAILED,
    LOG_PUBLISHED,
    LOG_RENDER_FAILED,
    LOG_RENDERED,
    LOG_REPOST,
    MESSAGE_BY_CODE,
    STATUS_APPROVED,
    STATUS_EXPIRED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_PROCESSING,
    STATUS_PUBLISHED,
    TEXT_DECIDED_EXPIRED,
    TEXT_FAILED,
    TEXT_PUBLISHED,
    TICK_PUBLISH_LIMIT,
    TICK_RENDER_LIMIT,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class RepostTickDeps:
    """Everything one pass needs. Graph pieces are None when unconfigured."""

    store: RepostStore
    studio: RepostStudio
    prompts: RepostPrompts
    metrics: OriginalMetrics
    clock: Clock
    reels: ReelGateway | None
    publisher: ReelPublisher | None


@dataclass
class _Budget:
    renders: int = TICK_RENDER_LIMIT
    publishes: int = TICK_PUBLISH_LIMIT


class RepostTick:
    """One pass. Returns how many drafts moved."""

    def __init__(self, deps: RepostTickDeps) -> None:
        self._deps = deps

    async def run(self) -> int:
        """Act on every due draft, within the per-tick budgets."""
        now = self._deps.clock.now()
        budget = _Budget()
        moved = 0
        for repost in await self._deps.store.due(now):
            moved += int(await self._step(repost, budget, now))
        return moved

    async def _step(self, repost: Repost, budget: _Budget, now: datetime) -> bool:
        if repost.status == STATUS_PENDING and now >= repost.expires_at:
            return await self._expire(repost, now)
        if repost.status == STATUS_PENDING and budget.renders > 0:
            budget.renders -= 1
            return await self._render(repost, now)
        if repost.status == STATUS_APPROVED and budget.publishes > 0:
            budget.publishes -= 1
            return await self._open_container(repost, now)
        if repost.status == STATUS_PROCESSING:
            return await self._poll(repost, now)
        return False

    async def _expire(self, repost: Repost, now: datetime) -> bool:
        expired = replace(repost, status=STATUS_EXPIRED, updated_at=now)
        if not await self._save(repost, expired):
            return False
        logger.info(LOG_REPOST, outcome=LOG_EXPIRED, repost_id=str(repost.id))
        if repost.telegram_message_id is not None:
            await self._deps.prompts.edit(
                repost.telegram_message_id, TEXT_DECIDED_EXPIRED
            )
        return True

    async def _render(self, repost: Repost, now: datetime) -> bool:
        try:
            files = await self._files(repost)
        except RepostRenderError as exc:
            logger.warning(LOG_REPOST, outcome=LOG_RENDER_FAILED, code=exc.code)
            failure = _Failure(
                code=exc.code, now=now, message=MESSAGE_BY_CODE.get(exc.code)
            )
            return await self._fail(repost, failure)
        ready = replace(repost, preview_ready_at=now, updated_at=now)
        if not await self._save(repost, ready):
            return False
        logger.info(LOG_REPOST, outcome=LOG_RENDERED, repost_id=str(repost.id))
        await self._notify(ready, files)
        return True

    async def _files(self, repost: Repost) -> RenderedFiles:
        reels = self._deps.reels
        try:
            reel = None if reels is None else await reels.reel(repost.media_id)
        except InstagramCallError:
            raise RepostRenderError(ERR_SOURCE_UNAVAILABLE) from None
        if reel is None:
            raise RepostRenderError(ERR_SOURCE_UNAVAILABLE)
        return await self._deps.studio.prepare(StudioJob(repost=repost, reel=reel))

    async def _notify(self, repost: Repost, files: RenderedFiles) -> None:
        link = None
        if not files.fits_telegram:
            link = self._deps.studio.public_url(repost, files.preview.name)
        notice = ApprovalNotice(
            repost=repost,
            metrics=await self._deps.metrics.metrics(repost.media_id),
            preview_link=link,
            source_size=files.source_size,
        )
        message_id = await self._deps.prompts.deliver(
            PromptDelivery(files=files, notice=notice)
        )
        if message_id is None:
            logger.warning(LOG_REPOST, outcome=LOG_NOTIFY_FAILED)
            return
        await self._save(repost, replace(repost, telegram_message_id=message_id))
        logger.info(LOG_REPOST, outcome=LOG_NOTIFIED, repost_id=str(repost.id))

    async def _open_container(self, repost: Repost, now: datetime) -> bool:
        publisher = self._deps.publisher
        if publisher is None:
            return False
        try:
            container_id = await publisher.create(self._container(repost))
        except InstagramCallError as exc:
            return await self._graph_failed(
                repost, _Failure(code=exc.error_code, now=now, transient=exc.transient)
            )
        processing = replace(
            repost,
            status=STATUS_PROCESSING,
            container_id=container_id,
            container_created_at=now,
            updated_at=now,
        )
        logger.info(LOG_REPOST, outcome=LOG_PROCESSING, repost_id=str(repost.id))
        return await self._save(repost, processing)

    def _container(self, repost: Repost) -> ContainerRequest:
        studio = self._deps.studio
        name = FILE_COVER if repost.cover_choice == COVER_GROK else FILE_ORIGINAL_COVER
        cover = studio.existing(repost, name)
        return ContainerRequest(
            video_url=studio.public_url(repost, FILE_PREVIEW),
            caption=repost.caption,
            cover_url=None if cover is None else studio.public_url(repost, cover.name),
            share_to_feed=repost.share_to_feed,
            collaborators=repost.collaborators,
        )

    async def _poll(self, repost: Repost, now: datetime) -> bool:
        publisher = self._deps.publisher
        if publisher is None or repost.container_id is None:
            return False
        try:
            state = await publisher.status(repost.container_id)
        except InstagramCallError as exc:
            return await self._graph_failed(
                repost, _Failure(code=exc.error_code, now=now, transient=exc.transient)
            )
        if state.code in {CONTAINER_FINISHED, CONTAINER_PUBLISHED}:
            return await self._publish(repost, now)
        failure = _container_failure(state, repost, now)
        if failure is None:
            return False
        return await self._fail(repost, failure)

    async def _publish(self, repost: Repost, now: datetime) -> bool:
        publisher = self._deps.publisher
        if publisher is None or repost.container_id is None:
            return False
        try:
            media_id = await publisher.publish(repost.container_id)
            permalink = await _permalink(publisher, media_id)
        except InstagramCallError as exc:
            return await self._graph_failed(
                repost,
                _Failure(
                    code=exc.error_code or ERR_PUBLISH_FAILED,
                    now=now,
                    transient=exc.transient,
                ),
            )
        published = replace(
            repost,
            status=STATUS_PUBLISHED,
            new_media_id=media_id,
            new_permalink=permalink,
            published_at=now,
            updated_at=now,
        )
        if not await self._save(repost, published):
            return False
        logger.info(LOG_REPOST, outcome=LOG_PUBLISHED, repost_id=str(repost.id))
        await self._deps.prompts.tell(
            TEXT_PUBLISHED.format(permalink=permalink or media_id)
        )
        return True

    async def _graph_failed(self, repost: Repost, failure: _Failure) -> bool:
        logger.warning(LOG_REPOST, outcome=LOG_PUBLISH_FAILED, code=failure.code)
        if failure.transient:
            return False
        return await self._fail(repost, failure)

    async def _fail(self, repost: Repost, failure: _Failure) -> bool:
        failed = replace(
            repost,
            status=STATUS_FAILED,
            error_code=failure.code,
            error_message=failure.message,
            updated_at=failure.now,
        )
        if not await self._save(repost, failed):
            return False
        if repost.status != STATUS_PENDING:
            await self._deps.prompts.tell(TEXT_FAILED.format(code=failure.code))
        return True

    async def _save(self, before: Repost, after: Repost) -> bool:
        saved = await self._deps.store.save(
            StatusChange(expected=before.status, repost=after)
        )
        await self._deps.store.commit()
        return saved


@dataclass(frozen=True, kw_only=True)
class _Failure:
    code: str
    now: datetime
    message: str | None = None
    transient: bool = False


async def _permalink(publisher: ReelPublisher, media_id: str) -> str | None:
    try:
        return await publisher.permalink(media_id)
    except InstagramCallError:
        return None


def _container_failure(
    state: ContainerState, repost: Repost, now: datetime
) -> _Failure | None:
    if state.code in {CONTAINER_ERROR, CONTAINER_EXPIRED}:
        return _Failure(code=ERR_CONTAINER_ERROR, now=now, message=state.detail)
    if _timed_out(repost, now):
        return _Failure(code=ERR_CONTAINER_TIMEOUT, now=now)
    return None


def _timed_out(repost: Repost, now: datetime) -> bool:
    started = repost.container_created_at or repost.updated_at or repost.created_at
    return now - started > timedelta(minutes=CONTAINER_TIMEOUT_MINUTES)


__all__ = [
    "RepostTick",
    "RepostTickDeps",
]
