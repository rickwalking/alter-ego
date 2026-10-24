"""Publish now from Telegram keeps the saved caption and posts it.

Feature: backend/tests/features/approve_keeps_caption_ae0542.feature

Drives the real owner action (``ap:pubnow``), the in-process editorial approve of
final review, the public release and the Instagram publish job against SQLite,
with the carousel's blog draft created by the real draft path (its
``distribution`` starts empty, as in prod).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import update

from rag_backend.domain.constants.blog_post import BlogPostOrigin
from rag_backend.domain.models.blog_generation_state import GenerationStart
from rag_backend.infrastructure.database.blog_generation_drafts import (
    GenerationDraftSpec,
    create_generation_draft,
)
from rag_backend.infrastructure.database.distribution_home import read_distribution
from rag_backend.infrastructure.database.models import CarouselProjectModel
from rag_backend.modules.autopilot.application.publish_job import (
    InstagramPublishJob,
    PublishJobDependencies,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.ports import CarouselMedia
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.infrastructure.carousel_source import (
    PublishingCarouselSource,
)
from rag_backend.modules.autopilot.infrastructure.publish_claims import (
    SqlPublishClaims,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.webhook_constants import KIND_CALLBACK
from rag_backend.modules.editorial.public import WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
from tests.integration.test_autopilot_hero_images import _World
from tests.integration.test_autopilot_scheduled_publish import (
    _BASE_URL,
    _OWNER_CHAT,
    _awaiting_run,
    _Clock,
    _owner_service,
    _project,
    _Story,
    world,
)
from tests.unit.modules.autopilot.test_instagram_publish_job import (
    _Gateway,
    _Notifier,
)

_CAPTION = "Legenda do Pedro, escrita a mao, depois da geracao, com #hashtags."

__all__ = ["world"]


class _CaptionGateway(_Gateway):
    def __init__(self) -> None:
        super().__init__()
        self.captions: list[str] = []

    async def open_carousel(self, media: CarouselMedia) -> str:
        self.captions.append(media.caption)
        return await super().open_carousel(media)


def _publish_job(
    world: _World, clock: _Clock, gateway: _Gateway
) -> InstagramPublishJob:
    repo = SqlAlchemyAutopilotRepository(world.session)
    return InstagramPublishJob(
        PublishJobDependencies(
            runs=repo,
            source=PublishingCarouselSource(world.session, _BASE_URL),
            gateway=gateway,
            notifier=_Notifier(),
            clock=clock,
            checkpoint=repo,
            claims=SqlPublishClaims(world.session),
            story=_Story(),
        )
    )


async def _save_caption_then_draft_blog(world: _World) -> None:
    await world.session.execute(
        update(CarouselProjectModel)
        .where(CarouselProjectModel.id == world.project_id)
        .values(caption=_CAPTION)
    )
    start = GenerationStart(
        kind="from_carousel",
        lease_id=uuid4().hex,
        now="2026-10-24T03:00:00Z",
        request={},
    )
    await create_generation_draft(
        world.session,
        GenerationDraftSpec(
            title="Agents that ship",
            slug=f"carousel-{world.project_id}",
            origin=BlogPostOrigin.CAROUSEL.value,
            author_id=str(uuid4()),
            start=start,
            project_id=world.project_id,
        ),
    )
    await world.session.commit()


@pytest.mark.asyncio
async def test_publish_now_keeps_the_saved_caption_and_posts_it(world: _World) -> None:
    """Scenario: Publish now keeps the saved caption and posts it"""
    clock = _Clock()
    run = await _awaiting_run(world)
    await _save_caption_then_draft_blog(world)
    service = _owner_service(world, clock)
    await service.handle(
        WebhookUpdate(
            update_id=7101,
            kind=KIND_CALLBACK,
            actor_id=_OWNER_CHAT,
            chat_id=_OWNER_CHAT,
            callback_id="cb-now",
            data=f"ap:pubnow:{run.run_id}",
            message_id=9,
        )
    )
    await world.session.commit()
    await service.deliver()

    approved = await SqlAlchemyAutopilotRepository(world.session).get(run.run_id)
    assert approved is not None
    assert approved.state is AutopilotRunState.PUBLISHING
    project = await _project(world)
    assert project.workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
    assert project.is_public is True
    assert project.caption == _CAPTION
    home = await read_distribution(world.session, world.project_id)
    assert home is not None
    assert home["caption"] == _CAPTION

    gateway = _CaptionGateway()
    assert await _publish_job(world, clock, gateway).tick() == 1
    assert gateway.captions == [_CAPTION]
