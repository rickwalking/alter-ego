"""``GET /api/instagram/insights`` over SQLite (AE-0378).

Gherkin: tests/features/instagram_insights.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.models import UserRole
from rag_backend.modules.autopilot.constants import STATUS_CANDIDATE_ACCEPTED
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.insights_models import (
    InstagramPostInsightsModel,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    ManualPublishModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.insights_constants import (
    APP_STATE_INSIGHTS_GATEWAY,
)
from tests.integration.conftest import auth_headers_for, create_test_user

_PATH = "/api/instagram/insights"
_RUN_MEDIA = "17900000000000001"
_MANUAL_MEDIA = "17900000000000002"


@dataclass
class _Graph:
    metrics: dict[str, InsightMetrics] = field(default_factory=dict)
    fail: bool = False
    calls: list[str] = field(default_factory=list)

    async def media_insights(self, media_id: str) -> InsightMetrics:
        self.calls.append(media_id)
        if self.fail:
            raise InstagramCallError(status_code=503, error_code="x", transient=True)
        return self.metrics.get(media_id, InsightMetrics())


@dataclass
class _Env:
    app: FastAPI
    client: AsyncClient


@pytest.fixture
async def env() -> AsyncIterator[_Env]:
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    editor = await create_test_user("insights@integration.test", UserRole.EDITOR)
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=auth_headers_for(editor),
    ) as client:
        yield _Env(app=app, client=client)
    db_config.c_engine = None
    await close_db()
    await engine.dispose()


async def _seed_posts() -> None:
    from rag_backend.infrastructure.database.config import get_session_maker

    now = datetime.now(UTC)
    topic_id = uuid4()
    async with get_session_maker()() as session:
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
                state=AutopilotRunState.PUBLISHED.value,
                state_reason=None,
                publish_attempts=1,
                telegram_message_ids=[],
                ig_post_id=_RUN_MEDIA,
                ig_permalink="https://instagram.com/p/run",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ManualPublishModel(
                carousel_project_id=str(uuid4()),
                state="published",
                ig_post_id=_MANUAL_MEDIA,
                ig_permalink="https://instagram.com/p/manual",
                claimed_at=now - timedelta(days=1),
            )
        )
        await session.commit()


async def _seed_snapshot(media_id: str, fetched_at: datetime) -> None:
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        session.add(
            InstagramPostInsightsModel(
                media_id=media_id, views=500, shares=5, follows=1, fetched_at=fetched_at
            )
        )
        await session.commit()


@pytest.mark.integration
class TestInsightsRoute:
    # Scenario: Fresh insights for published posts
    # Scenario: Missing metric
    @pytest.mark.asyncio
    async def test_fresh_rows_and_missing_metric(self, env: _Env) -> None:
        await _seed_posts()
        graph = _Graph(
            metrics={
                _RUN_MEDIA: InsightMetrics(views=1000, shares=10, saved=40, follows=3),
                _MANUAL_MEDIA: InsightMetrics(views=200, shares=2, saved=4),
            }
        )
        setattr(env.app.state, APP_STATE_INSIGHTS_GATEWAY, graph)

        body = (await env.client.get(_PATH)).json()

        assert [item["media_id"] for item in body["items"]] == [
            _RUN_MEDIA,
            _MANUAL_MEDIA,
        ]
        first, second = body["items"]
        assert first["views"] == 1000
        assert first["follows"] == 3
        assert first["shares_per_100_views"] == 1.0
        assert first["permalink"] == "https://instagram.com/p/run"
        assert second["follows"] is None
        assert not first["stale"]
        assert body["follows_per_post"] == 3.0
        assert body["shares_per_100_views"] == 1.0
        assert body["configured"] is True

        # The snapshots were stored: a second read does not call Graph.
        again = (await env.client.get(_PATH)).json()
        assert len(graph.calls) == 2
        assert again["items"][0]["views"] == 1000

    # Scenario: Graph failure keeps the last snapshot
    @pytest.mark.asyncio
    async def test_failure_keeps_the_stale_snapshot(self, env: _Env) -> None:
        await _seed_posts()
        await _seed_snapshot(_RUN_MEDIA, datetime.now(UTC) - timedelta(hours=8))
        setattr(env.app.state, APP_STATE_INSIGHTS_GATEWAY, _Graph(fail=True))

        body = (await env.client.get(_PATH)).json()

        run_row = next(i for i in body["items"] if i["media_id"] == _RUN_MEDIA)
        assert run_row["views"] == 500
        assert run_row["stale"] is True
        manual_row = next(i for i in body["items"] if i["media_id"] == _MANUAL_MEDIA)
        assert manual_row["views"] is None
        assert manual_row["stale"] is True

    # Scenario: No Instagram account configured
    @pytest.mark.asyncio
    async def test_unconfigured(self, env: _Env) -> None:
        await _seed_posts()
        body = (await env.client.get(_PATH)).json()
        assert body["configured"] is False
        assert all(item["stale"] for item in body["items"])

    # Scenario: Only editors read insights
    @pytest.mark.asyncio
    async def test_anonymous_is_rejected(self, env: _Env) -> None:
        response = await env.client.get(_PATH, headers={"Authorization": ""})
        assert response.status_code == 401
