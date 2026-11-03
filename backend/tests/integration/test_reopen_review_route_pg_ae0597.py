"""Reopen, then a fresh approve restores the approval, on Postgres.

Feature: tests/features/reopen_review_on_cover_switch_ae0597.feature. The app
over an isolated Postgres schema holding every table and an in-memory
LangGraph checkpointer parked at the approved hold; the website cover switch
through the real stack (fake bridge, recorded render) with the real checkpoint
reopen. Then the real approve route refuses a review page read before the
switch (it would queue the resume for the generation worker), and the
run-owned approve the worker and Telegram run (``run_automation_phase`` over the real
``EditorialWorkflowService`` on that checkpointer) restores
``approved_for_publish``. Skipped without a Postgres ``DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import update

import rag_backend.infrastructure.database.config as db_config
from rag_backend.agents.carousel_workflow_engine import CarouselWorkflowEngine
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING_HUMAN,
    REVIEW_ACTION_APPROVE,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.models import User, UserRole
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.public import (
    AutomationRun,
    CheckpointEngineReopener,
    run_automation_phase,
)
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.reopen_review_pg_support import APPROVED
from tests.integration.website_cover_review_pg_support import (
    Harness,
    harness,
    row,
    seed,
    website_task,
)

_APPROVE = {"action": REVIEW_ACTION_APPROVE, "reviewer_id": "user-1"}


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "out"))
    get_settings.cache_clear()
    yield assets
    get_settings.cache_clear()


@dataclass(frozen=True, kw_only=True)
class _Rig:
    client: AsyncClient
    built: Harness
    owner: User
    checkpointer: InMemorySaver


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
            owner = await create_test_user("owner@ae0597.test", UserRole.EDITOR)
            app = create_app()
            checkpointer = InMemorySaver()
            app.state.carousel_checkpointer = checkpointer
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers=auth_headers_for(owner),
            ) as client:
                yield _Rig(
                    client=client, built=built, owner=owner, checkpointer=checkpointer
                )
        finally:
            limiter.reset()
            db_config.c_engine = previous


async def _held(rig: _Rig, project_id: str) -> CarouselWorkflowEngine:
    """A checkpoint approved and parked at the approved hold."""
    engine = CarouselWorkflowEngine(checkpointer=rig.checkpointer)
    await engine.start(
        project_id,
        {"topic": "AI"},
        research_findings=[{"source": "report", "key_points": ["risk"]}],
    )
    for _ in range(6):
        await engine.resume(project_id, _APPROVE)
    return engine


async def _owned_by_the_caller(rig: _Rig, project_id: str) -> None:
    async with rig.built.sessions()() as session:
        await session.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == project_id)
            .values(owner_id=str(rig.owner.id))
        )
        await session.commit()


@requires_postgres
@pytest.mark.asyncio
async def test_a_reopened_carousel_is_approved_again_through_the_route(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The switch reopens the row and the checkpoint; the approve at the new
    version restores ``approved_for_publish``."""
    # Scenario: A fresh approve restores the approval
    async with _app(monkeypatch) as rig:
        project_id, photos = await seed(rig.built, dirs, **APPROVED)
        engine = await _held(rig, project_id)
        checkpoint = CheckpointEngineReopener(rig.checkpointer)

        await (await website_task(rig.built, project_id, photos[0], checkpoint))()

        reopened = await row(rig.built, project_id)
        assert reopened.workflow_status == "draft"
        assert reopened.lock_version == 4
        state = await engine.get_state(project_id)
        assert state is not None
        assert state["current_phase"] == PHASE_FINAL_REVIEW
        assert state["phase_status"] == PHASE_STATUS_AWAITING_HUMAN

        await _owned_by_the_caller(rig, project_id)
        stale = await rig.client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "approve", "expected_version": 3},
        )
        assert stale.status_code == 409, stale.text

        await _approve_as_the_worker(rig, project_id)

        approved = await row(rig.built, project_id)
        assert approved.workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
        held = await engine.get_state(project_id)
        assert held is not None
        assert held["workflow_status"] == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH


async def _approve_as_the_worker(rig: _Rig, project_id: str) -> None:
    """The run-owned final-review approve at the reopened version."""
    service = EditorialWorkflowService(
        EditorialWorkflowConfig(llm=MagicMock(), checkpointer=rig.checkpointer)
    )
    async with rig.built.sessions()() as session:
        await run_automation_phase(
            AutomationRun(
                engine=service,
                session=session,
                project_id=project_id,
                expected_version=4,
                action=REVIEW_ACTION_APPROVE,
            )
        )
