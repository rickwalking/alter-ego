"""Shared helpers for carousel consolidation integration tests."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
from httpx import AsyncClient

from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_AUTH
from rag_backend.domain.models import (
    CarouselProject,
    CarouselStatus,
    CarouselTheme,
    User,
    UserRole,
)

TEST_SECRET = "test-secret-for-carousel-consolidation-tests!!"


def parse_sse_events(text: str) -> list[dict[str, object]]:
    """Parse raw SSE response text into event dicts."""
    events: list[dict[str, object]] = []
    buffer = ""
    for line in text.split("\n"):
        if line.startswith("data: "):
            buffer = line[6:]
            continue
        if line == "" and buffer:
            try:
                parsed = json.loads(buffer)
            except json.JSONDecodeError:
                buffer = ""
                continue
            if isinstance(parsed, dict):
                events.append(parsed)
            buffer = ""
    if buffer:
        try:
            parsed = json.loads(buffer)
        except json.JSONDecodeError:
            return events
        if isinstance(parsed, dict):
            events.append(parsed)
    return events


async def _empty_sse_listen(
    project_id: str,
    keepalive_seconds: float = 30,
) -> AsyncIterator[dict[str, object]]:
    """Terminate SSE immediately after the initial snapshot (test helper)."""
    del project_id, keepalive_seconds
    if False:
        yield {}


async def get_workflow_stream_status(
    client: AsyncClient,
    project_id: str,
    headers: dict[str, str],
) -> int:
    """Return HTTP status for the workflow SSE route without blocking on the body."""
    response = await client.get(
        f"/api/carousels/{project_id}/workflow/stream",
        headers=headers,
    )
    return response.status_code


async def fetch_workflow_stream_snapshot(
    client: AsyncClient,
    project_id: str,
    headers: dict[str, str],
) -> tuple[int, list[dict[str, object]]]:
    """Fetch the initial SSE snapshot via a finite response body.

    httpx ASGITransport deadlocks on long-lived ``client.stream`` reads, so tests
    patch ``WorkflowSseHub.listen`` to exit after the connect snapshot.
    """
    with patch(
        "rag_backend.application.services.carousel.workflow_sse_hub.WorkflowSseHub.listen",
        _empty_sse_listen,
    ):
        response = await client.get(
            f"/api/carousels/{project_id}/workflow/stream",
            headers=headers,
        )
    if response.status_code != 200:
        return response.status_code, []
    return response.status_code, parse_sse_events(response.text)


async def collect_hub_events_during(
    project_id: str,
    action: Callable[[], Awaitable[None]],
    *,
    expected_count: int = 1,
    timeout: float = 5.0,
) -> list[dict[str, object]]:
    """Collect workflow SSE hub events emitted while ``action`` runs."""
    from rag_backend.application.services.carousel.editorial_workflow_support import (
        SSE_EVENT_KEEPALIVE,
    )
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        SSE_EVENT_KEY,
        get_workflow_sse_hub,
    )

    hub = get_workflow_sse_hub()
    received: list[dict[str, object]] = []

    async def listen() -> None:
        async for event in hub.listen(project_id, keepalive_seconds=0.05):
            if event.get(SSE_EVENT_KEY) == SSE_EVENT_KEEPALIVE:
                continue
            received.append(event)
            if len(received) >= expected_count:
                break

    listener = asyncio.create_task(listen())
    await asyncio.sleep(0)
    await asyncio.wait_for(asyncio.gather(action(), listener), timeout=timeout)
    return received


async def create_user(email: str, role: UserRole) -> User:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = PostgresUserRepository(session)
        user = User(
            email=email,
            full_name=email.split("@")[0].title(),
            role=role,
            hashed_password="not-used",
        )
        created = await repo.create(user)
        await session.commit()
        return created


def auth_header(user: User) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "type": JWT_TYPE_AUTH,
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        },
        TEST_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


async def create_carousel(
    owner: User,
    *,
    is_public: bool = False,
    blog_markdown: str | None = "# Draft\n\nBody",
) -> str:
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )
    from rag_backend.infrastructure.database.config import get_session_maker

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = PostgresCarouselRepository(session)
        project = CarouselProject(
            topic="Consolidation Test",
            audience="Devs",
            niche="AI",
            theme=CarouselTheme.AI_COMPETITION,
            owner_id=str(owner.id),
            is_public=is_public,
            blog_markdown=blog_markdown,
            output_dir="/tmp/test-carousel-output",
        )
        created = await repo.create_project(project)
        await session.commit()
        return str(created.id)


async def set_carousel_status(project_id: str, status: CarouselStatus) -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

    session_maker = get_session_maker()
    async with session_maker() as session:
        model = await session.get(CarouselProjectModel, project_id)
        if model is not None:
            model.status = status.value
            await session.commit()


async def set_workflow_status(project_id: str, workflow_status: str) -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

    session_maker = get_session_maker()
    async with session_maker() as session:
        model = await session.get(CarouselProjectModel, project_id)
        if model is not None:
            model.workflow_status = workflow_status
            await session.commit()


async def seed_workflow_assigned_reviewer(
    client: AsyncClient,
    project_id: str,
    reviewer_id: str,
) -> None:
    from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
    from rag_backend.application.services.carousel.workflow_state import (
        get_initial_carousel_state,
    )
    from rag_backend.domain.constants.carousel_workflow import (
        PHASE_RESEARCH,
        PHASE_STATUS_AWAITING_HUMAN,
    )

    checkpointer = client.app.state.carousel_checkpointer  # type: ignore[attr-defined]
    engine = CarouselWorkflowEngine(checkpointer=checkpointer)
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
            "assigned_reviewer_id": reviewer_id,
            "current_phase": PHASE_RESEARCH,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        },
    )
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

    session_maker = get_session_maker()
    async with session_maker() as session:
        model = await session.get(CarouselProjectModel, project_id)
        if model is not None:
            model.assigned_reviewer_id = reviewer_id
            await session.commit()


async def seed_workflow_phase(
    client: AsyncClient,
    project_id: str,
    *,
    phase: str,
    phase_status: str,
    extra_state: dict[str, object] | None = None,
) -> None:
    from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
    from rag_backend.application.services.carousel.workflow_state import (
        get_initial_carousel_state,
    )

    checkpointer = client.app.state.carousel_checkpointer  # type: ignore[attr-defined]
    engine = CarouselWorkflowEngine(checkpointer=checkpointer)
    brief = {"topic": "Test", "audience": "Devs", "brief": "Brief", "sources": []}
    initial = get_initial_carousel_state(project_id, brief)
    await engine.start(
        project_id,
        brief,
        research_findings=list(initial.get("research_findings") or []),
    )
    state_update: dict[str, object] = {
        "current_phase": phase,
        "phase_status": phase_status,
    }
    if extra_state:
        state_update.update(extra_state)
    await engine.update_state(project_id, state_update)

    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

    session_maker = get_session_maker()
    async with session_maker() as session:
        model = await session.get(CarouselProjectModel, project_id)
        if model is not None:
            model.current_phase = phase
            model.phase_status = phase_status
            await session.commit()


async def get_lock_version(project_id: str) -> int:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

    session_maker = get_session_maker()
    async with session_maker() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        return int(model.lock_version or 1)


async def set_project_phase_progress(
    project_id: str,
    phase_progress: dict[str, object],
) -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

    session_maker = get_session_maker()
    async with session_maker() as session:
        model = await session.get(CarouselProjectModel, project_id)
        if model is not None:
            model.phase_progress = phase_progress
            await session.commit()


async def drain_background_tasks() -> None:
    """Allow fire-and-forget workflow resume tasks to finish in tests."""
    for _ in range(30):
        pending = [
            task
            for task in asyncio.all_tasks()
            if task.get_name().startswith("workflow-resume-")
        ]
        if not pending:
            return
        await asyncio.sleep(0.05)
    await asyncio.sleep(0.1)


async def wait_for_workflow_state(
    client: AsyncClient,
    project_id: str,
    headers: dict[str, str],
    *,
    phase: str | None = None,
    phase_status: str | None = None,
    timeout: float = 10.0,
) -> dict[str, object]:
    """Poll workflow state until expected phase fields are present."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        response = await client.get(
            f"/api/carousels/{project_id}/workflow/state",
            headers=headers,
        )
        if response.status_code == 200:
            payload = response.json()
            if phase is not None and payload.get("current_phase") != phase:
                await asyncio.sleep(0.05)
                continue
            if phase_status is not None and payload.get("phase_status") != phase_status:
                await asyncio.sleep(0.05)
                continue
            return payload
        await asyncio.sleep(0.05)
    raise AssertionError("Timed out waiting for workflow state")
