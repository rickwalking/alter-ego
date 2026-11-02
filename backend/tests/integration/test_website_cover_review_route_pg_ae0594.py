"""The real approve route refuses a review page read before the website switch.

Feature: tests/features/website_cover_review_switch_ae0594.feature. The app over
an isolated Postgres schema holding every table, an in-memory checkpointer at
final review, the website cover switch through the real stack (fake bridge,
recorded render). Skipped without a Postgres ``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import update

import rag_backend.infrastructure.database.config as db_config
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_VERSION_CONFLICT,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING_HUMAN,
)
from rag_backend.domain.models import User, UserRole
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.website_cover_review_pg_support import (
    Harness,
    harness,
    row,
    seed,
    website_task,
)


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "out"))
    get_settings.cache_clear()
    yield assets
    get_settings.cache_clear()


@asynccontextmanager
async def _app(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Rig]:
    """The app over a fresh schema, the harness on the same engine, the owner."""
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter

    async with isolated_schema(list(Base.metadata.tables)) as engine:
        previous = db_config.c_engine
        db_config.c_engine = engine
        limiter.reset()
        try:
            built = harness(engine, monkeypatch)
            owner = await create_test_user("owner@ae0594.test", UserRole.EDITOR)
            app = create_app()
            checkpointer = InMemorySaver()
            app.state.carousel_checkpointer = checkpointer
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                headers=auth_headers_for(owner),
            ) as client:
                yield _Rig(
                    client=client, built=built, owner=owner, checkpointer=checkpointer
                )
        finally:
            limiter.reset()
            db_config.c_engine = previous


@dataclass(frozen=True, kw_only=True)
class _Rig:
    client: AsyncClient
    built: Harness
    owner: User
    checkpointer: InMemorySaver


async def _at_final_review(rig: _Rig, project_id: str) -> None:
    """A checkpoint waiting at the final-review interrupt."""
    from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
    from rag_backend.application.services.carousel.workflow_state import (
        get_initial_carousel_state,
    )

    engine = CarouselWorkflowEngine(checkpointer=rig.checkpointer)
    brief = {"topic": "Test", "audience": "Devs", "brief": "Brief", "sources": []}
    initial = get_initial_carousel_state(project_id, brief)
    await engine.start(
        project_id,
        brief,
        research_findings=list(initial.get("research_findings") or []),
    )
    await engine.update_state(
        project_id,
        {
            "current_phase": PHASE_FINAL_REVIEW,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        },
    )


async def _hand_to_the_caller(rig: _Rig, project_id: str) -> None:
    """The caller (the app's authenticated owner) owns the carousel."""
    async with rig.built.sessions()() as session:
        await session.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == project_id)
            .values(owner_id=str(rig.owner.id))
        )
        await session.commit()


@requires_postgres
@pytest.mark.asyncio
async def test_approve_route_with_the_version_read_before_the_switch_is_409(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The page read version 3; after the switch the route answers a conflict."""
    # Scenario: A website approval read before the switch is refused
    async with _app(monkeypatch) as rig:
        project_id, photos = await seed(rig.built, dirs)
        await _at_final_review(rig, project_id)
        await (await website_task(rig.built, project_id, photos[0]))()
        await _hand_to_the_caller(rig, project_id)
        switched = await row(rig.built, project_id)
        assert switched.lock_version == 4

        response = await rig.client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "approve", "expected_version": 3},
        )

        assert response.status_code == 409, response.text
        assert CONFLICT_CODE_VERSION_CONFLICT in response.text
        model = await row(rig.built, project_id)
        assert model.lock_version == 4
        assert model.workflow_status == "draft"
        assert model.phase_status == PHASE_STATUS_AWAITING_HUMAN

        fresh = await rig.client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "approve", "expected_version": 4},
        )
        assert fresh.status_code == 202, fresh.text
