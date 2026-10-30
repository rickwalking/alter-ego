"""``GET /api/editorial-analytics`` counts published carousels per channel.

Feature: analytics_publishing_channels_ae0500.feature
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from rag_backend.domain.models import UserRole
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.constants import STATUS_CANDIDATE_ACCEPTED
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    ManualPublishModel,
    TopicCandidateModel,
)
from tests.integration.conftest import auth_headers_for, create_test_user

PATH = "/api/editorial-analytics"


async def _published_post(author_id: str) -> None:
    session_maker = get_session_maker()
    async with session_maker() as session:
        session.add(
            BlogPostModel.from_entity({
                "title": "Post",
                "slug": f"post-{uuid4().hex[:8]}",
                "status": "published",
                "content": {},
                "author_id": author_id,
                "published_at": datetime.now(UTC),
            })
        )
        await session.commit()


async def _published_carousel(owner_id: str, media_id: str) -> None:
    now = datetime.now(UTC)
    session_maker = get_session_maker()
    async with session_maker() as session:
        project = CarouselProjectModel(
            topic="t", audience="a", niche="n", owner_id=owner_id
        )
        session.add(project)
        await session.flush()
        topic_id = uuid4()
        session.add(
            TopicCandidateModel(
                id=topic_id,
                title="Agents",
                angle="a",
                why_viral="w",
                audience="devs",
                niche="ai",
                brief="b",
                sources=["https://x.com/a/status/1"],
                score=80,
                signal_hash=uuid4().hex,
                status=STATUS_CANDIDATE_ACCEPTED,
            )
        )
        await session.flush()
        session.add(
            AutopilotRunModel(
                id=uuid4(),
                topic_candidate_id=topic_id,
                carousel_project_id=project.id,
                state=AutopilotRunState.PUBLISHED.value,
                state_reason=None,
                publish_attempts=1,
                telegram_message_ids=[],
                ig_post_id=media_id,
                ig_permalink=f"https://instagram.com/p/{media_id}",
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()


async def _manual_carousel(owner_id: str, media_id: str) -> None:
    session_maker = get_session_maker()
    async with session_maker() as session:
        project = CarouselProjectModel(
            topic="t", audience="a", niche="n", owner_id=owner_id
        )
        session.add(project)
        await session.flush()
        session.add(
            ManualPublishModel(
                carousel_project_id=project.id,
                state="published",
                ig_post_id=media_id,
                ig_permalink=f"https://instagram.com/p/{media_id}",
                claimed_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        await session.commit()


@pytest.mark.integration
class TestEditorialAnalyticsChannels:
    @pytest.mark.asyncio
    async def test_carousels_count_per_channel(self, client: AsyncClient) -> None:
        """Scenario: Published carousels count in Publicados and the velocity chart."""
        editor = await create_test_user(
            f"channels-{uuid4().hex[:6]}@test.com", UserRole.EDITOR
        )
        headers = auth_headers_for(editor)
        await _published_post(str(editor.id))
        await _published_carousel(str(editor.id), "17900000000000011")
        await _manual_carousel(str(editor.id), "17900000000000012")

        body = (await client.get(PATH, headers=headers)).json()

        assert body["summary"]["published_this_week"] == 3
        channels = {c["channel"]: c for c in body["summary"]["channels"]}
        assert channels["blog"]["published_total"] == 1
        assert channels["carousel"]["published_total"] == 2
        last_week = body["velocity_by_week"][-1]
        assert last_week["published_count"] == 3
        assert last_week["channels"] == {"blog": 1, "carousel": 2}

    @pytest.mark.asyncio
    async def test_editor_scoping_counts_own_carousels(
        self, client: AsyncClient
    ) -> None:
        """Scenario: An editor sees only their own carousels."""
        editor = await create_test_user(
            f"scoping-{uuid4().hex[:6]}@test.com", UserRole.EDITOR
        )
        other = await create_test_user(
            f"other-{uuid4().hex[:6]}@test.com", UserRole.EDITOR
        )
        await _published_carousel(str(editor.id), "17900000000000021")
        await _published_carousel(str(other.id), "17900000000000022")

        body = (await client.get(PATH, headers=auth_headers_for(editor))).json()

        channels = {c["channel"]: c for c in body["summary"]["channels"]}
        assert channels["carousel"]["published_total"] == 1
        assert channels["carousel"]["published_this_week"] == 1

    @pytest.mark.asyncio
    async def test_average_views_is_gone(self, client: AsyncClient) -> None:
        """Scenario: The average_views dead field is removed."""
        body = (await client.get(PATH)).json()

        assert "average_views" not in body["summary"]
        channels = body["summary"]["channels"]
        assert all("average_views" not in c for c in channels)

    @pytest.mark.asyncio
    async def test_anonymous_is_rejected(self, client: AsyncClient) -> None:
        """An anonymous caller gets 401 from the analytics endpoint."""
        response = await client.get(PATH, headers={"Authorization": ""})
        assert response.status_code == 401
