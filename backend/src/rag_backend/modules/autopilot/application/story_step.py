"""Post the Story that announces a carousel, once (AE-0369).

Runs after the carousel's media id is stored, under the same publish claim.
A stored ``published`` row short-circuits with no Graph call. The container
id is committed before ``media_publish``, so a crash resumes that container
(or, past 24 hours, checks whether it was already published) instead of
posting a second Story. Transient Graph errors are retried up to three
attempts. Every failure is recorded and returned; nothing is raised, so the
carousel's published state never depends on the Story.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from rag_backend.modules.autopilot.application.publish_steps import (
    reusable_container,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.music import music_style_for
from rag_backend.modules.autopilot.domain.ports import Clock, PublishCheckpoint
from rag_backend.modules.autopilot.domain.publish import PostExtras, StoredContainer
from rag_backend.modules.autopilot.domain.story import (
    SaveStoryContainer,
    SaveStoryResult,
    StoryGateway,
    StoryMedia,
    StoryMediaSource,
    StoryRunner,
    StoryStore,
)
from rag_backend.modules.autopilot.story_constants import (
    LOG_STORY_FAILED,
    LOG_STORY_PUBLISHED,
    MUSIC_DEFAULT,
    REASON_STORY_CAROUSEL_MISSING,
    REASON_STORY_IMAGE_MISSING,
    REASON_STORY_UNEXPECTED,
    STORY_MAX_ATTEMPTS,
    STORY_OUTCOME_FAILED,
    STORY_OUTCOME_PUBLISHED,
    STORY_STATE_FAILED,
    STORY_STATE_PUBLISHED,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class StoryDependencies:
    """Collaborators for the Story step. The checkpoint commits the shared session."""

    store: StoryStore
    media: StoryMediaSource
    gateway: StoryGateway
    checkpoint: PublishCheckpoint
    clock: Clock


@dataclass(frozen=True, kw_only=True)
class _Outcome:
    status: str
    error: str | None


class InstagramStoryStep:
    """One Story per carousel."""

    def __init__(self, deps: StoryDependencies) -> None:
        self._deps = deps

    async def run(self, project_id: str) -> PostExtras:
        """Post the Story, or report why not. Never raises."""
        media: StoryMedia | None = None
        try:
            media = await self._deps.media.load(project_id)
            outcome = await self._story(project_id, media)
        except Exception as exc:
            # The carousel is already live; the Story must not undo that.
            logger.warning(LOG_STORY_FAILED, error=type(exc).__name__)
            outcome = _Outcome(
                status=STORY_OUTCOME_FAILED, error=REASON_STORY_UNEXPECTED
            )
        return PostExtras(
            story_status=outcome.status,
            story_error=outcome.error,
            music_style=_music(media),
        )

    async def _story(self, project_id: str, media: StoryMedia | None) -> _Outcome:
        record = await self._deps.store.get(project_id)
        if record is not None and record.state == STORY_STATE_PUBLISHED:
            return _Outcome(status=STORY_OUTCOME_PUBLISHED, error=None)
        if media is None:
            return await self._failed(project_id, REASON_STORY_CAROUSEL_MISSING)
        if media.image_url is None:
            return await self._failed(project_id, REASON_STORY_IMAGE_MISSING)
        return await self._attempts(project_id, media.image_url)

    async def _attempts(self, project_id: str, image_url: str) -> _Outcome:
        attempt = 1
        while True:
            try:
                media_id = await self._attempt(project_id, image_url)
            except InstagramCallError as exc:
                if exc.transient and attempt < STORY_MAX_ATTEMPTS:
                    attempt += 1
                    continue
                return await self._failed(project_id, exc.error_code)
            return await self._published(project_id, media_id)

    async def _attempt(self, project_id: str, image_url: str) -> str | None:
        """Resume the stored container when it is safe, else open one."""
        record = await self._deps.store.get(project_id)
        stored = record.container if record is not None else None
        now = self._deps.clock.now()
        container = await reusable_container(self._deps.gateway, stored, now)
        if container is None:
            container = await self._open(project_id, image_url)
        return await self._deps.gateway.finish_story(container)

    async def _open(self, project_id: str, image_url: str) -> StoredContainer:
        created_at = self._deps.clock.now()
        container_id = await self._deps.gateway.open_story(image_url)
        container = StoredContainer(container_id=container_id, created_at=created_at)
        await self._deps.store.save_container(
            SaveStoryContainer(project_id=project_id, container=container)
        )
        await self._deps.checkpoint.commit()
        return container

    async def _published(self, project_id: str, media_id: str | None) -> _Outcome:
        await self._save(
            SaveStoryResult(
                project_id=project_id,
                state=STORY_STATE_PUBLISHED,
                media_id=media_id,
                error=None,
                at=self._deps.clock.now(),
            )
        )
        logger.info(LOG_STORY_PUBLISHED, project_id=project_id, media_id=media_id)
        return _Outcome(status=STORY_OUTCOME_PUBLISHED, error=None)

    async def _failed(self, project_id: str, reason: str) -> _Outcome:
        await self._save(
            SaveStoryResult(
                project_id=project_id,
                state=STORY_STATE_FAILED,
                media_id=None,
                error=reason,
                at=self._deps.clock.now(),
            )
        )
        logger.warning(LOG_STORY_FAILED, project_id=project_id, error=reason)
        return _Outcome(status=STORY_OUTCOME_FAILED, error=reason)

    async def _save(self, result: SaveStoryResult) -> None:
        await self._deps.store.save_result(result)
        await self._deps.checkpoint.commit()


async def post_extras(
    runner: StoryRunner | None, project_id: str | None
) -> PostExtras | None:
    """The Story step's result, or None when there is no Story to post."""
    if runner is None or not project_id:
        return None
    return await runner.run(project_id)


def _music(media: StoryMedia | None) -> str:
    if media is None:
        return MUSIC_DEFAULT
    return music_style_for(media.niche, media.image_style)
