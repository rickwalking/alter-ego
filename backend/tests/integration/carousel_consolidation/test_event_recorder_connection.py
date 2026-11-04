"""A dropped event write cannot break the workflow it was recording.

Feature: carousel_generation_log_ae0556.feature

Every recorder statement under test outlasts the real 100 ms budget, so the
recorder timeout cancels each write while that statement is in flight. The suite's
``client`` gives the recorder its own connection, the way each production session
holds its own, so the cancelled writes are dropped and the revise still completes.
On the workflow's one ``StaticPool`` connection a cancelled insert stays in the
workflow's transaction, so its next commit stores the event the recorder reported
as dropped. A cancelled run lookup leaves its cursor alive past its connection's
close, and in rollback-journal mode that read lock fails the workflow's commit with
``database is locked``.
"""

from __future__ import annotations

import asyncio
import gc
import time
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

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
    GenerationRunModel,
)
from tests.integration.carousel_consolidation.event_connections import EventConnections
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    create_carousel,
    create_user,
    drain_background_tasks,
    get_lock_version,
    seed_workflow_phase,
)

EVENT_INSERT = f"INSERT INTO {CarouselGenerationEventModel.__tablename__}"
RUN_READ = f"SELECT {GenerationRunModel.__tablename__}."
REVISE_FEEDBACK = "Slide 2 tone is too formal"


class _HeldStatements:
    """Hold each recorder statement with ``prefix`` past the budget, in the driver.

    The hold runs in SQLite's trace callback, on the thread that executes the
    statement, so the event loop keeps running: the budget expires while the
    statement is in flight, and the workflow can queue statements behind it, as on
    a busy runner. Any hold longer than the budget is enough: the timer is due
    before the statement can return, so asyncio cancels the write right there even
    when the loop is late.

    ``EventConnections`` installs the callback on each connection as it is opened,
    so a reconnect after a cancelled write is held too.
    """

    def __init__(self, connections: EventConnections, prefix: str) -> None:
        self.connections = connections
        self.prefix = prefix
        self.held = 0
        self.completed = 0

    def __call__(self, statement: str) -> None:
        if not statement.startswith(self.prefix):
            return
        self.held += 1
        time.sleep(EVENT_WRITE_TIMEOUT_SECONDS * 3)

    def count_completed(self, *args: object) -> None:
        """``after_cursor_execute``: a held recorder statement must never return."""
        connection = args[0]
        statement = args[2]
        if not isinstance(connection, Connection) or not isinstance(statement, str):
            return
        driver = connection.connection.driver_connection
        if statement.startswith(self.prefix) and self.connections.owns(driver):
            self.completed += 1


@contextmanager
def _holding(
    event_connections: EventConnections, prefix: str
) -> Iterator[_HeldStatements]:
    hold = _HeldStatements(event_connections, prefix)
    event_connections.trace_statements(hold)
    sqlalchemy_event.listen(Engine, "after_cursor_execute", hold.count_completed)
    try:
        yield hold
    finally:
        sqlalchemy_event.remove(Engine, "after_cursor_execute", hold.count_completed)


@pytest.fixture
def slow_event_inserts(
    event_connections: EventConnections,
) -> Iterator[_HeldStatements]:
    with _holding(event_connections, EVENT_INSERT) as hold:
        yield hold


@pytest.fixture
def slow_run_reads(event_connections: EventConnections) -> Iterator[_HeldStatements]:
    with _holding(event_connections, RUN_READ) as hold:
        yield hold


async def _revise_through_the_worker(client: AsyncClient) -> None:
    """Queue a content revise and run it the way the generation worker does."""
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


async def _stored_events() -> list[UUID]:
    async with get_session_maker()() as session:
        return list(await session.scalars(select(CarouselGenerationEventModel.id)))


async def test_cancelled_event_writes_leave_the_workflow_intact(
    client: AsyncClient, slow_event_inserts: _HeldStatements
) -> None:
    """Scenario: Recorder timeout preserves authoritative generation state"""
    await _revise_through_the_worker(client)

    assert slow_event_inserts.held > 0
    assert slow_event_inserts.completed == 0
    assert await _stored_events() == []


async def test_a_cancelled_event_read_does_not_lock_the_workflow(
    client: AsyncClient, slow_run_reads: _HeldStatements
) -> None:
    """Scenario: Recorder timeout preserves authoritative generation state

    Each write is cancelled during its run lookup, which leaves that cursor alive
    after its connection is closed. The workflow's own commits still go through.
    """
    gc.disable()
    try:
        await _revise_through_the_worker(client)
    finally:
        gc.enable()

    assert slow_run_reads.held > 0
    assert slow_run_reads.completed == 0
    assert await _stored_events() == []
