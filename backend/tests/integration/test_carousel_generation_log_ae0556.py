"""Owner-safe generation event persistence and paginated carousel API.

Feature: carousel_generation_log_ae0556.feature
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.generation_queue.application.generation_events import (
    generation_event_scope,
    record_generation_event,
)
from rag_backend.modules.generation_queue.domain.failure_metadata import (
    safe_failure_metadata,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEventInput,
    GenerationEventRun,
)
from rag_backend.modules.generation_queue.domain.models import GenerationKind
from rag_backend.modules.generation_queue.infrastructure.generation_events import (
    SqlGenerationEventRecorder,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    CarouselGenerationEventModel,
    GenerationRunModel,
)
from tests.integration.carousel_copy_support import CopyEnv, copy_env_context

if TYPE_CHECKING:
    from httpx import AsyncClient, Response

BASE_TIME = datetime(2026, 10, 26, 12, tzinfo=UTC)
PLANTED_SECRET = "stored-planted-secret"
PLANTED_SQL = "SELECT secret FROM generation_runs WHERE token = %(token)s"


@pytest_asyncio.fixture
async def log_env(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[CopyEnv, None]:
    async with copy_env_context(tmp_path, monkeypatch) as env:
        yield env


async def _seed_run(project_id: str) -> UUID:
    from rag_backend.infrastructure.database.config import get_session_maker

    run_id = uuid4()
    async with get_session_maker()() as session:
        session.add(
            GenerationRunModel(
                id=run_id,
                kind=GenerationKind.WORKFLOW_RESUME.value,
                dedupe_key=f"resume:{project_id}:{run_id}",
                status="succeeded",
                payload={},
                carousel_project_id=project_id,
                attempts=2,
                phase_attempts={"content": 1},
                last_error_code="transient",
                created_at=BASE_TIME,
                started_at=BASE_TIME + timedelta(seconds=1),
                finished_at=BASE_TIME + timedelta(seconds=8),
                updated_at=BASE_TIME + timedelta(seconds=8),
            )
        )
        await session.commit()
    return run_id


async def _seed_nullable_autopilot(project_id: str) -> tuple[UUID, UUID]:
    from rag_backend.infrastructure.database.config import get_session_maker

    parent_id, run_id = uuid4(), uuid4()
    topic_id = uuid4()
    async with get_session_maker()() as session:
        session.add(
            TopicCandidateModel(
                id=topic_id,
                title="Nullable parent",
                angle="a",
                why_viral="w",
                audience="a",
                niche="n",
                brief="b",
                sources=["https://example.com/a"],
                score=1,
                signal_hash=uuid4().hex,
                status="promoted",
            )
        )
        session.add(
            AutopilotRunModel(
                id=parent_id,
                topic_candidate_id=topic_id,
                carousel_project_id=project_id,
                state="generating",
                publish_attempts=0,
                telegram_message_ids=[],
                created_at=BASE_TIME,
                updated_at=BASE_TIME,
            )
        )
        session.add(
            GenerationRunModel(
                id=run_id,
                kind="autopilot_drive",
                dedupe_key=f"autopilot:{parent_id}",
                status="running",
                payload={"autopilot_run_id": str(parent_id)},
                autopilot_run_id=str(parent_id),
                carousel_project_id=None,
                attempts=1,
                phase_attempts={},
                created_at=BASE_TIME,
                updated_at=BASE_TIME,
            )
        )
        await session.commit()
    return parent_id, run_id


def _event_row(
    project_id: str, run_id: UUID, sequence: int
) -> CarouselGenerationEventModel:
    return CarouselGenerationEventModel(
        id=uuid4(),
        generation_run_id=run_id,
        carousel_project_id=project_id,
        kind=GenerationKind.WORKFLOW_RESUME.value,
        event_type="phase_succeeded" if sequence % 2 else "image_job_succeeded",
        phase="content" if sequence % 2 else "images",
        outcome="succeeded",
        occurred_at=BASE_TIME + timedelta(microseconds=sequence),
        duration_ms=1250 + sequence,
        attempt=1,
        details={"image_job_id": str(uuid4()), "size": "1536x1024"},
    )


async def _seed_events(
    project_id: str, run_id: UUID, count: int, start: int = 0
) -> list[UUID]:
    from rag_backend.infrastructure.database.config import get_session_maker

    rows = [
        _event_row(project_id, run_id, index) for index in range(start, start + count)
    ]
    async with get_session_maker()() as session:
        session.add_all(rows)
        await session.commit()
    return [row.id for row in rows]


async def _log(
    client: AsyncClient, project_id: str, params: dict[str, object] | None = None
) -> Response:
    return await client.get(
        f"/api/carousels/{project_id}/generation-log", params=params
    )


async def test_complete_timeline_is_owner_and_admin_only(log_env: CopyEnv) -> None:
    """Scenario: Generation log access is owner and admin only"""
    project_id = await log_env.seed_carousel()
    run_id = await _seed_run(project_id)
    await _seed_events(project_id, run_id, 2)
    async with log_env.client_for(log_env.owner) as client:
        owner = await _log(client, project_id)
    async with log_env.client_for(log_env.admin) as client:
        admin = await _log(client, project_id)
    await log_env.set_project(
        project_id, {"assigned_reviewer_id": str(log_env.other.id)}
    )
    async with log_env.client_for(log_env.other) as client:
        refused = await _log(client, project_id)
        missing = await _log(client, str(uuid4()))
    async with log_env.anonymous_client() as client:
        anonymous = await _log(client, project_id)

    assert owner.status_code == 200, owner.text
    assert admin.status_code == 200
    assert refused.status_code == 403
    assert missing.status_code == 404
    assert anonymous.status_code == 401
    body = owner.json()
    assert body["runs"][0]["kind"] == "workflow_resume"
    assert body["runs"][0]["attempts"] == 2
    assert body["runs"][0]["error_code"] == "transient"
    assert body["runs"][0]["duration_ms"] == 7000
    assert body["events"][0]["duration_ms"] == 1251
    assert body["events"][0]["phase"] == "content"
    assert body["events"][1]["event_type"] == "image_job_succeeded"
    assert "payload" not in body["runs"][0]
    assert "last_error" not in body["runs"][0]


async def test_stored_rows_and_api_exclude_sensitive_failure_content(
    log_env: CopyEnv,
) -> None:
    """Scenario: Stored events exclude sensitive failure content"""
    project_id = await log_env.seed_carousel()
    run_id = await _seed_run(project_id)
    failure = DBAPIError(
        PLANTED_SQL, {"token": PLANTED_SECRET}, Exception(PLANTED_SECRET)
    )
    failure_metadata = safe_failure_metadata(failure, "database_error")
    event = GenerationEventInput(
        event_type="run_dead_letter",
        outcome="failed",
        error_code=failure_metadata["error_code"],
        details={
            "error_type": failure_metadata["error_type"],
            "prompt": PLANTED_SECRET,
            "statement": PLANTED_SQL,
            "params": {"token": PLANTED_SECRET},
        },
    )
    from rag_backend.infrastructure.database.config import get_session_maker

    async with generation_event_scope(
        GenerationEventRun(
            id=run_id,
            kind=GenerationKind.WORKFLOW_RESUME,
            carousel_project_id=project_id,
        ),
        SqlGenerationEventRecorder(get_session_maker()),
    ):
        assert await record_generation_event(event) is True
        stored = await record_generation_event(
            GenerationEventInput(
                event_type="phase_artifacts",
                outcome="succeeded",
                langfuse_trace_id="a" * 32,
                langfuse_trace_url="https://cloud.langfuse.com/project/p1/traces/"
                + "a" * 32,
            )
        )
    assert stored is True

    async with get_session_maker()() as session:
        rows = (await session.scalars(select(CarouselGenerationEventModel))).all()
        serialized = json.dumps(
            [
                {
                    column.name: getattr(row, column.name)
                    for column in row.__table__.columns
                }
                for row in rows
            ],
            default=str,
        )
    assert len(rows) == 2
    assert PLANTED_SECRET not in serialized
    assert PLANTED_SQL not in serialized
    assert rows[0].details == {"error_type": "DBAPIError", "truncated": True}
    async with log_env.client_for(log_env.owner) as client:
        response = await _log(client, project_id)
    assert response.status_code == 200
    assert PLANTED_SECRET not in response.text
    assert PLANTED_SQL not in response.text
    trace_events = [
        item for item in response.json()["events"] if item["langfuse_trace_url"]
    ]
    assert trace_events[0]["langfuse_trace_id"] == "a" * 32


async def test_keyset_pages_are_bounded_and_stable_during_inserts(
    log_env: CopyEnv,
) -> None:
    """Scenario: Generation log pages are stable during new events"""
    project_id = await log_env.seed_carousel()
    run_id = await _seed_run(project_id)
    seeded = await _seed_events(project_id, run_id, 201)
    async with log_env.client_for(log_env.owner) as client:
        first = await _log(client, project_id, {"limit": 200})
        assert first.status_code == 200, first.text
        cursor = first.json()["next_cursor"]
        await _seed_events(project_id, run_id, 1, start=1000)
        second = await _log(client, project_id, {"limit": 200, "before": cursor})
        other_project = await log_env.seed_carousel()
        foreign_cursor = seeded[0]
        invalid = await _log(client, other_project, {"before": foreign_cursor})

    assert len(first.json()["events"]) == 200
    assert second.status_code == 200
    assert len(second.json()["events"]) == 1
    returned = [item["id"] for item in first.json()["events"]]
    returned += [item["id"] for item in second.json()["events"]]
    assert len(returned) == len(set(returned)) == 201
    assert set(returned) == {str(event_id) for event_id in seeded}
    assert second.json()["next_cursor"] is None
    assert invalid.status_code == 422


async def test_mismatched_run_summary_is_not_exposed(log_env: CopyEnv) -> None:
    """Scenario: Generation log access is owner and admin only"""
    project_a = await log_env.seed_carousel()
    project_b = await log_env.seed_carousel()
    run_a = await _seed_run(project_a)
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        session.add(_event_row(project_b, run_a, 99))
        await session.commit()
    async with log_env.client_for(log_env.owner) as client:
        response = await _log(client, project_b)

    assert response.status_code == 200
    assert response.json()["events"] == []
    assert response.json()["runs"] == []


async def test_nullable_autopilot_mismatch_is_rejected(log_env: CopyEnv) -> None:
    """Scenario: Generation log access is owner and admin only"""
    project_a = await log_env.seed_carousel()
    project_b = await log_env.seed_carousel()
    parent_id, run_id = await _seed_nullable_autopilot(project_a)
    from rag_backend.infrastructure.database.config import get_session_maker

    async with generation_event_scope(
        GenerationEventRun(
            id=run_id,
            kind=GenerationKind.AUTOPILOT_DRIVE,
            carousel_project_id=project_b,
            autopilot_run_id=str(parent_id),
        ),
        SqlGenerationEventRecorder(get_session_maker()),
    ):
        assert (
            await record_generation_event(
                GenerationEventInput(event_type="run_started", outcome="running")
            )
            is False
        )
    async with get_session_maker()() as session:
        session.add(_event_row(project_b, run_id, 101))
        await session.commit()
    async with log_env.client_for(log_env.owner) as client:
        response = await _log(client, project_b)

    assert response.status_code == 200
    assert response.json()["events"] == []
    assert response.json()["runs"] == []


async def test_default_page_size_and_limit_validation(log_env: CopyEnv) -> None:
    """Scenario: Generation log pages are stable during new events"""
    project_id = await log_env.seed_carousel()
    run_id = await _seed_run(project_id)
    await _seed_events(project_id, run_id, 60)
    async with log_env.client_for(log_env.owner) as client:
        response = await _log(client, project_id)
        zero = await _log(client, project_id, {"limit": 0})
        excessive = await _log(client, project_id, {"limit": 201})

    assert response.status_code == 200
    assert len(response.json()["events"]) == 50
    assert response.json()["next_cursor"] is not None
    assert zero.status_code == 422
    assert excessive.status_code == 422
