"""The ``connector`` block of ``GET /api/instagram/insights``.

Gherkin: tests/features/instagram_insights.feature (connector scenarios)
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
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.infrastructure.insights_models import (
    InstagramPostInsightsModel,
)
from rag_backend.modules.autopilot.insights_constants import (
    APP_STATE_INSIGHTS_GATEWAY,
)
from tests.integration.conftest import auth_headers_for, create_test_user

_PATH = "/api/instagram/insights"
_MEDIA = "17900000000000041"


@dataclass
class _Graph:
    metrics: dict[str, InsightMetrics] = field(default_factory=dict)
    fail: bool = False

    async def media_insights(self, media_id: str) -> InsightMetrics:
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
    editor = await create_test_user("connector@integration.test", UserRole.EDITOR)
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


async def _seed_published_and_snapshot(fetched_at: datetime) -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.modules.autopilot.infrastructure.models import (
        ManualPublishModel,
    )

    async with get_session_maker()() as session:
        session.add(
            ManualPublishModel(
                carousel_project_id=str(uuid4()),
                state="published",
                ig_post_id=_MEDIA,
                ig_permalink="https://instagram.com/p/c",
                claimed_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        session.add(
            InstagramPostInsightsModel(
                media_id=_MEDIA, views=500, fetched_at=fetched_at
            )
        )
        await session.commit()


@pytest.mark.integration
class TestConnectorBlock:
    @pytest.mark.asyncio
    async def test_fresh_connector_reports_last_sync(self, env: _Env) -> None:
        """Scenario: The connector block reports the last sync."""
        await _seed_published_and_snapshot(datetime.now(UTC) - timedelta(hours=1))
        setattr(
            env.app.state,
            APP_STATE_INSIGHTS_GATEWAY,
            _Graph(metrics={_MEDIA: InsightMetrics(views=600)}),
        )

        body = (await env.client.get(_PATH)).json()

        connector = body["connector"]
        assert connector["channel"] == "instagram"
        assert connector["configured"] is True
        assert connector["stale"] is False
        assert connector["error"] is None
        assert connector["last_sync_at"] is not None

    @pytest.mark.asyncio
    async def test_stale_connector_reports_error_and_last_sync(self, env: _Env) -> None:
        """Scenario: A stale connector says when it last synced."""
        stale_at = datetime.now(UTC) - timedelta(hours=8)
        await _seed_published_and_snapshot(stale_at)
        setattr(env.app.state, APP_STATE_INSIGHTS_GATEWAY, _Graph(fail=True))

        body = (await env.client.get(_PATH)).json()

        connector = body["connector"]
        assert connector["stale"] is True
        assert connector["error"] == "x"
        assert connector["last_sync_at"] is not None

    @pytest.mark.asyncio
    async def test_unconfigured_connector(self, env: _Env) -> None:
        """Scenario: An unconfigured connector is named instead of zeros."""
        await _seed_published_and_snapshot(datetime.now(UTC) - timedelta(hours=1))

        body = (await env.client.get(_PATH)).json()

        connector = body["connector"]
        assert connector["configured"] is False
        assert connector["stale"] is False
        assert connector["last_sync_at"] is not None
        assert body["items"][0]["views"] == 500
