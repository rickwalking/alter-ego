"""A dropped event write cannot break the workflow it was recording.

Feature: carousel_generation_log_ae0556.feature

Every event insert here outlasts the real 100 ms budget, so the recorder timeout
cancels each one while its statement is in flight. The suite's ``client`` gives the
recorder its own connection, the way each production session holds its own, so the
cancelled writes are dropped and the revise still completes. On the workflow's one
``StaticPool`` connection the cancelled insert stays in the workflow's transaction, so
its next commit stores the event the recorder reported as dropped.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator

import pytest
from httpx import AsyncClient
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_STATUS_AWAITING_HUMAN,
)
from rag_backend.domain.models import UserRole
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.modules.generation_queue.domain.generation_events import (
    EVENT_WRITE_TIMEOUT_SECONDS,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    CarouselGenerationEventModel,
)
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    create_carousel,
    create_user,
    drain_background_tasks,
    get_lock_version,
    seed_workflow_phase,
)

EVENT_INSERT = f"INSERT INTO {CarouselGenerationEventModel.__tablename__}"
REVISE_FEEDBACK = "Slide 2 tone is too formal"


class _SlowEventInserts:
    """Hold every event insert past the budget inside the driver's own thread.

    The hold runs in SQLite's trace callback, on the thread that executes the
    statement, so the event loop keeps running: the budget expires while the insert
    is in flight, and the workflow can queue statements behind it, as on a busy runner.
    """

    def __init__(self) -> None:
        self.held = 0
        self._traced: set[int] = set()

    def arm(self, *args: object) -> None:
        connection = args[0]
        statement = args[2]
        if not isinstance(connection, Connection) or not isinstance(statement, str):
            return
        if not statement.startswith(EVENT_INSERT):
            return
        dbapi_connection = connection.connection.dbapi_connection
        if dbapi_connection is None or id(dbapi_connection) in self._traced:
            return
        self._traced.add(id(dbapi_connection))
        dbapi_connection.run_async(lambda raw: raw.set_trace_callback(self._hold))

    def _hold(self, statement: str) -> None:
        if not statement.startswith(EVENT_INSERT):
            return
        self.held += 1
        time.sleep(EVENT_WRITE_TIMEOUT_SECONDS * 3)


@pytest.fixture
def slow_event_inserts() -> Iterator[_SlowEventInserts]:
    listener = _SlowEventInserts()
    sqlalchemy_event.listen(Engine, "before_cursor_execute", listener.arm)
    yield listener
    sqlalchemy_event.remove(Engine, "before_cursor_execute", listener.arm)


async def test_cancelled_event_writes_leave_the_workflow_intact(
    client: AsyncClient, slow_event_inserts: _SlowEventInserts
) -> None:
    """Scenario: Recorder timeout preserves authoritative generation state"""
    editor = await create_user("event-connection@example.com", UserRole.EDITOR)
    project_id = await create_carousel(editor, is_public=False)
    await seed_workflow_phase(
        client,
        project_id,
        phase=PHASE_CONTENT,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        extra_state={
            "slide_drafts": [{"draft_text": "Formal slide copy"}],
            "outline": [{"slide_index": 1, "title": "Intro", "key_points": []}],
        },
    )
    version = await get_lock_version(project_id)
    response = await client.post(
        f"/api/carousels/{project_id}/workflow/resume",
        json={
            "action": "revise",
            "feedback": REVISE_FEEDBACK,
            "expected_version": version,
        },
        headers=auth_header(editor),
    )
    assert response.status_code == 202

    await drain_background_tasks(client)
    await asyncio.sleep(EVENT_WRITE_TIMEOUT_SECONDS * 3)

    assert slow_event_inserts.held > 0
    state_response = await client.get(
        f"/api/carousels/{project_id}/workflow/state", headers=auth_header(editor)
    )
    assert state_response.status_code == 200
    phase_feedback = state_response.json().get("phase_feedback", {})
    assert isinstance(phase_feedback, dict)
    stored_feedback = [
        note
        for notes in phase_feedback.values()
        if isinstance(notes, list)
        for note in notes
    ]
    assert REVISE_FEEDBACK in stored_feedback
    async with get_session_maker()() as session:
        events = list(await session.scalars(select(CarouselGenerationEventModel.id)))
    assert events == []
