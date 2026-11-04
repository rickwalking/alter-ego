"""A stale owner review after a system reject is refused, on Postgres.

Feature: tests/features/reject_bumps_lock_version_ae0604.feature. The app runs
over an isolated Postgres schema holding every table, with an in-memory
LangGraph checkpointer parked at the research gate. The owner reads the
carousel through the real state route, the real stuck-workflow sweep or the
real abandoned-escalation settle rejects it on its own committed session, then
the owner's resume goes through the real resume route and its lock_version
compare-and-swap. Skipped without a Postgres ``DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import rag_backend.infrastructure.database.config as db_config
from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_CAROUSEL_REJECTED,
    CONFLICT_CODE_VERSION_CONFLICT,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_REJECTED,
    REVIEW_ACTION_APPROVE,
)
from rag_backend.domain.models import User, UserRole
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.workflow_timeout_repository import (
    WorkflowTimeoutRepository,
)
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
)
from rag_backend.modules.editorial.public import (
    AbandonedCarouselSettle,
    settle_abandoned_carousel,
)
from tests.integration.carousel_consolidation.helpers import create_carousel
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

pytestmark = pytest.mark.usefixtures("no_outbox_relay", "asset_dirs")

_TIMEOUT_HOURS = 72
_FINDINGS = [{"title": "F", "summary": "D"}]


@dataclass(frozen=True, kw_only=True)
class _Rig:
    client: AsyncClient
    engine: AsyncEngine
    checkpointer: InMemorySaver
    owner: User


@asynccontextmanager
async def _app() -> AsyncIterator[_Rig]:
    """The app over a fresh schema with the owner's auth headers."""
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter

    async with isolated_schema(list(Base.metadata.tables)) as engine:
        previous = db_config.c_engine
        db_config.c_engine = engine
        limiter.reset()
        try:
            owner = await create_test_user("owner@ae0604.test", UserRole.EDITOR)
            app = create_app()
            checkpointer = InMemorySaver()
            app.state.carousel_checkpointer = checkpointer
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers=auth_headers_for(owner),
            ) as client:
                yield _Rig(
                    client=client,
                    engine=engine,
                    checkpointer=checkpointer,
                    owner=owner,
                )
        finally:
            limiter.reset()
            db_config.c_engine = previous


def _sessions(rig: _Rig) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(rig.engine, expire_on_commit=False)


async def _waiting_carousel(rig: _Rig) -> str:
    """A carousel and its checkpoint waiting for a human at research, idle long."""
    project_id = await create_carousel(rig.owner)
    workflow = CarouselWorkflowEngine(checkpointer=rig.checkpointer)
    brief = {"topic": "Test", "audience": "Devs", "brief": "Brief", "sources": []}
    await workflow.start(project_id, brief, research_findings=_FINDINGS)
    await workflow.update_state(
        project_id,
        {
            "current_phase": PHASE_RESEARCH,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            "research_findings": _FINDINGS,
        },
    )
    idle = datetime.now(UTC) - timedelta(hours=_TIMEOUT_HOURS + 1)
    async with _sessions(rig)() as session:
        await session.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == project_id)
            .values(
                current_phase=PHASE_RESEARCH,
                phase_status=PHASE_STATUS_AWAITING_HUMAN,
                updated_at=idle,
            )
        )
        await session.commit()
    return project_id


def _events() -> WorkflowEventService:
    return WorkflowEventService(MemoryEventPublisher())


async def _owner_reads(rig: _Rig, project_id: str) -> int:
    """The lock version the owner's review page shows."""
    state = await rig.client.get(f"/api/carousels/{project_id}/workflow/state")
    assert state.status_code == 200, state.text
    assert state.json()["phase_status"] == PHASE_STATUS_AWAITING_HUMAN
    return int(state.json()["lock_version"])


async def _sweep(rig: _Rig) -> int:
    """One stuck-workflow sweep on its own session, committed like the tick."""
    async with _sessions(rig)() as session:
        rejected = await WorkflowTimeoutRepository(_events()).auto_reject_stuck(
            session, _TIMEOUT_HOURS
        )
        await session.commit()
    return rejected


async def _settle(rig: _Rig, project_id: str, escalated_at: int) -> bool:
    """The abandoned-escalation settle on its own session, committed."""
    async with _sessions(rig)() as session:
        settled = await settle_abandoned_carousel(
            session,
            _events(),
            AbandonedCarouselSettle(
                project_id=project_id,
                expected_version=escalated_at,
                idle_hours=_TIMEOUT_HOURS,
            ),
        )
        await session.commit()
    return settled


async def _approve(rig: _Rig, project_id: str, version: int) -> tuple[int, str]:
    response = await rig.client.post(
        f"/api/carousels/{project_id}/workflow/resume",
        json={"action": REVIEW_ACTION_APPROVE, "expected_version": version},
    )
    return response.status_code, response.text


async def _row(rig: _Rig, project_id: str) -> CarouselProjectModel:
    async with _sessions(rig)() as session:
        found = await session.get(CarouselProjectModel, project_id)
        assert found is not None
        return found


async def _assert_refused_and_rejected(
    rig: _Rig, project_id: str, read_at: int
) -> None:
    status_code, body = await _approve(rig, project_id, read_at)
    assert status_code == 409, body
    assert CONFLICT_CODE_VERSION_CONFLICT in body
    after = await _row(rig, project_id)
    assert after.phase_status == PHASE_STATUS_REJECTED
    assert after.lock_version == read_at + 1


# Scenario: A stale owner approve after a stuck-sweep reject is refused
@requires_postgres
@pytest.mark.asyncio
async def test_a_stale_approve_after_the_sweep_reject_is_refused() -> None:
    async with _app() as rig:
        project_id = await _waiting_carousel(rig)
        read_at = await _owner_reads(rig, project_id)

        assert await _sweep(rig) == 1

        await _assert_refused_and_rejected(rig, project_id, read_at)


# Scenario: A stale owner approve after an escalation-close settle is refused
@requires_postgres
@pytest.mark.asyncio
async def test_a_stale_approve_after_the_escalation_settle_is_refused() -> None:
    async with _app() as rig:
        project_id = await _waiting_carousel(rig)
        read_at = await _owner_reads(rig, project_id)

        assert await _settle(rig, project_id, read_at) is True

        await _assert_refused_and_rejected(rig, project_id, read_at)


# Scenario: An approve at the post-reject version is refused as carousel_rejected
# Scenario: A website approve on a rejected carousel is refused
@requires_postgres
@pytest.mark.asyncio
async def test_an_approve_at_the_post_reject_version_is_refused() -> None:
    async with _app() as rig:
        project_id = await _waiting_carousel(rig)
        read_at = await _owner_reads(rig, project_id)
        assert await _sweep(rig) == 1
        current = (await _row(rig, project_id)).lock_version

        status_code, body = await _approve(rig, project_id, current)

        assert current == read_at + 1
        assert status_code == 409, body
        assert CONFLICT_CODE_CAROUSEL_REJECTED in body
        after = await _row(rig, project_id)
        assert after.phase_status == PHASE_STATUS_REJECTED
        assert after.lock_version == current


# Scenario: An owner action at the current version on a waiting carousel still works
@requires_postgres
@pytest.mark.asyncio
async def test_an_approve_at_the_current_version_on_a_waiting_carousel_works() -> None:
    async with _app() as rig:
        project_id = await _waiting_carousel(rig)
        read_at = await _owner_reads(rig, project_id)

        status_code, body = await _approve(rig, project_id, read_at)

        assert status_code == 202, body
        after = await _row(rig, project_id)
        assert after.phase_status == PHASE_STATUS_IN_PROGRESS
        assert after.lock_version == read_at + 1
