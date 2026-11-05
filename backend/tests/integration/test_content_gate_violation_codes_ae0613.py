"""Stored content-gate rows and the log API hold rule ids, never slide content.

Feature: content_gate_violation_codes_ae0613.feature
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from rag_backend.modules.generation_queue.application.generation_events import (
    generation_event_scope,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEventInput,
    GenerationEventRun,
)
from rag_backend.modules.generation_queue.domain.models import GenerationKind
from rag_backend.modules.generation_queue.events_public import record_phase_artifacts
from rag_backend.modules.generation_queue.infrastructure.generation_events import (
    SqlGenerationEventRecorder,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    CarouselGenerationEventModel,
    GenerationRunModel,
)
from tests.integration.carousel_copy_support import CopyEnv, copy_env_context

BASE_TIME = datetime(2026, 11, 4, 12, tzinfo=UTC)
PLANTED_MESSAGE = "planted violation message"
PLANTED_TEXT = "Planted Slide Heading From The Owner"


@dataclass
class _CapturingRecorder:
    """Keep events so the store write skips the 100 ms best-effort budget."""

    events: list[GenerationEventInput] = field(default_factory=list)

    async def record(
        self, run: GenerationEventRun, event: GenerationEventInput
    ) -> bool:
        self.events.append(event)
        return True


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
                status="running",
                payload={},
                carousel_project_id=project_id,
                attempts=1,
                phase_attempts={},
                created_at=BASE_TIME,
                updated_at=BASE_TIME,
            )
        )
        await session.commit()
    return run_id


async def test_row_and_api_hold_the_code_and_no_slide_content(
    log_env: CopyEnv,
) -> None:
    """Scenario: A violation with a message and slide text stores the code only"""
    from rag_backend.infrastructure.database.config import get_session_maker

    project_id = await log_env.seed_carousel()
    run = GenerationEventRun(
        id=await _seed_run(project_id),
        kind=GenerationKind.WORKFLOW_RESUME,
        carousel_project_id=project_id,
    )
    report = {
        "validation_status": "invalid",
        "blocking": True,
        "violations": [
            {
                "code": "heading_not_sentence_case_en",
                "message": PLANTED_MESSAGE,
                "field": PLANTED_TEXT,
                "text": PLANTED_TEXT,
                "severity": "blocker",
            },
            {"code": PLANTED_TEXT, "message": PLANTED_MESSAGE},
        ],
    }
    capture = _CapturingRecorder()
    async with generation_event_scope(run, capture):
        await record_phase_artifacts(
            "content", {"content_gate_validation": report}, None
        )
    gate = next(e for e in capture.events if e.event_type == "content_gate")
    assert await SqlGenerationEventRecorder(get_session_maker()).record(run, gate)

    async with get_session_maker()() as session:
        row = (await session.scalars(select(CarouselGenerationEventModel))).one()
        stored = json.dumps(
            {c.name: getattr(row, c.name) for c in row.__table__.columns},
            default=str,
        )
    async with log_env.client_for(log_env.owner) as client:
        response = await client.get(f"/api/carousels/{project_id}/generation-log")

    assert response.status_code == 200, response.text
    assert row.details == {
        "violation_count": 2,
        "blocking_count": 1,
        "violation_codes": "heading_not_sentence_case_en",
        "truncated": True,
    }
    assert response.json()["events"][0]["details"] == row.details
    for planted in (PLANTED_MESSAGE, PLANTED_TEXT):
        assert planted not in stored
        assert planted not in response.text
