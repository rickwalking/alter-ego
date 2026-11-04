"""Real recorder timeouts preserve the authoritative generation tables.

Feature: carousel_generation_log_ae0556.feature
"""

from __future__ import annotations

import asyncio
import time

from httpx import AsyncClient
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy import select

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_OUTLINE,
    PHASE_STATUS_AWAITING_HUMAN,
)
from rag_backend.domain.models import UserRole
from rag_backend.infrastructure.database import config as db_config
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.generation_queue.application.generation_events import (
    generation_event_run,
    generation_event_scope,
    record_generation_event,
)
from rag_backend.modules.generation_queue.constants import (
    EVENT_RUN_STARTED,
    OUTCOME_RUNNING,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    EVENT_WRITE_TIMEOUT_SECONDS,
    GenerationEventInput,
)
from rag_backend.modules.generation_queue.infrastructure.generation_events import (
    SqlGenerationEventRecorder,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    CarouselGenerationEventModel,
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    SqlGenerationRunStore,
)
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    create_carousel,
    create_user,
    get_lock_version,
    seed_workflow_phase,
)


async def test_recorder_timeout_preserves_authoritative_generation_state(
    client: AsyncClient,
) -> None:
    """Scenario: Recorder timeout preserves authoritative generation state"""
    editor = await create_user("event-timeout@example.com", UserRole.EDITOR)
    project_id = await create_carousel(editor, is_public=False)
    await seed_workflow_phase(
        client,
        project_id,
        phase=PHASE_OUTLINE,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        extra_state={"outline": [{"slide_index": 1, "title": "Intro"}]},
    )
    version = await get_lock_version(project_id)
    response = await client.post(
        f"/api/carousels/{project_id}/workflow/resume",
        json={"action": "approve", "expected_version": version},
        headers=auth_header(editor),
    )
    assert response.status_code == 202
    sessions = get_session_maker()
    async with sessions() as session:
        run_id = await session.scalar(
            select(GenerationRunModel.id).where(
                GenerationRunModel.carousel_project_id == project_id
            )
        )
    assert run_id is not None
    run = await SqlGenerationRunStore(sessions).get(run_id)
    assert run is not None
    engine = db_config.c_engine
    assert engine is not None
    delayed = False

    def delay_first_statement(*args: object) -> None:
        nonlocal delayed
        if delayed:
            return
        delayed = True
        time.sleep(EVENT_WRITE_TIMEOUT_SECONDS * 3)

    sqlalchemy_event.listen(
        engine.sync_engine, "before_cursor_execute", delay_first_statement
    )
    try:
        async with generation_event_scope(
            generation_event_run(run), SqlGenerationEventRecorder(sessions)
        ):
            recorded = await record_generation_event(
                GenerationEventInput(
                    event_type=EVENT_RUN_STARTED, outcome=OUTCOME_RUNNING
                )
            )
    finally:
        sqlalchemy_event.remove(
            engine.sync_engine, "before_cursor_execute", delay_first_statement
        )
    await asyncio.sleep(EVENT_WRITE_TIMEOUT_SECONDS * 3)

    assert recorded is False
    assert delayed is True
    async with sessions() as session:
        project = await session.get(CarouselProjectModel, project_id)
        stored_run = await session.get(GenerationRunModel, run_id)
        events = list(await session.scalars(select(CarouselGenerationEventModel.id)))
    assert project is not None
    assert stored_run is not None
    assert events == []
