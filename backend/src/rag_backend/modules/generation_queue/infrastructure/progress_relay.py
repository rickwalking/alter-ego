"""Workflow SSE events from the worker process to the web process.

The SSE hub is in-process, and phases now run in the worker. The worker installs a
hub that also sends each event as ``NOTIFY carousel_progress``; the web listens on
that channel and publishes the events into its own hub, where the open editors
are subscribed. NOTIFY is fire-and-forget, so nothing depends on it: every SSE
(re)connect still starts from the current workflow state.

A NOTIFY payload must stay under 8000 bytes. A ``review_required`` event that is
larger travels without its gate snapshot and a ``refetch`` mark; the web rebuilds
the gate from the checkpoint. Other oversized events (large artifact updates) are
dropped: the phase change and the review event that follow carry the same state.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.application.services.carousel.carousel_run_stage import (
    clear_run_stage,
    set_run_stage,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_sse_build import (
    EventParams,
    build_review_gate_payload,
    build_review_required_event,
)
from rag_backend.application.services.carousel.editorial_workflow_sse_constants import (
    SSE_EVENT_REVIEW_REQUIRED,
    SSE_PAYLOAD_FIELD_EVENT,
    SSE_PAYLOAD_FIELD_GATE,
)
from rag_backend.application.services.carousel.workflow_sse_hub import (
    WorkflowSseHub,
    get_workflow_sse_hub,
)
from rag_backend.domain.constants.carousel_run import (
    SSE_EVENT_RUN_FINISHED,
    SSE_EVENT_RUN_STAGE_CHANGED,
    SSE_PAYLOAD_FIELD_RUN_STAGE,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_AWAITING_HUMAN
from rag_backend.modules.generation_queue.constants import (
    LOG_RELAY_FAILED,
    MAX_NOTIFY_BYTES,
    PROGRESS_CHANNEL,
)
from rag_backend.modules.generation_queue.infrastructure.raw_connection import (
    asyncpg_connection,
)

logger = structlog.get_logger()

FIELD_PROJECT = "p"
FIELD_EVENT = "e"
FIELD_REFETCH = "refetch"
RECONNECT_SECONDS = 5.0
_NOTIFY_SQL = text("SELECT pg_notify(:channel, :payload)")

Event = dict[str, object]
Notifier = Callable[[str], Awaitable[None]]
GateRefetch = Callable[[str], Awaitable[Event | None]]
EngineFactory = Callable[[], EditorialWorkflowService]


def encode(project_id: str, event: Event) -> str | None:
    """The NOTIFY payload for an event, slimmed or None when it cannot fit."""
    payload = json.dumps({FIELD_PROJECT: project_id, FIELD_EVENT: event}, default=str)
    if len(payload.encode()) <= MAX_NOTIFY_BYTES:
        return payload
    if event.get(SSE_PAYLOAD_FIELD_EVENT) != SSE_EVENT_REVIEW_REQUIRED:
        return None
    slim = {**event, SSE_PAYLOAD_FIELD_GATE: None, FIELD_REFETCH: True}
    return json.dumps({FIELD_PROJECT: project_id, FIELD_EVENT: slim}, default=str)


def decode(payload: str) -> tuple[str, Event] | None:
    """(project id, event) from a NOTIFY payload; None when malformed."""
    try:
        data = json.loads(payload)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    project_id, event = data.get(FIELD_PROJECT), data.get(FIELD_EVENT)
    if not isinstance(project_id, str) or not isinstance(event, dict):
        return None
    return project_id, {str(key): value for key, value in event.items()}


def engine_notifier(engine: AsyncEngine) -> Notifier:
    """Send one NOTIFY on a pooled connection (the worker's progress events)."""

    async def notify(payload: str) -> None:
        async with engine.connect() as connection:
            await connection.execute(
                _NOTIFY_SQL, {"channel": PROGRESS_CHANNEL, "payload": payload}
            )
            await connection.commit()

    return notify


class RelayingWorkflowSseHub(WorkflowSseHub):
    """The worker's hub: local fan-out plus ``NOTIFY`` to the web."""

    def __init__(self, notifier: Notifier) -> None:
        super().__init__()
        self._notifier = notifier

    async def publish(self, project_id: str, event: Event) -> None:
        """Publish locally, then relay; a failed relay never fails the phase."""
        await super().publish(project_id, event)
        payload = encode(project_id, event)
        if payload is None:
            return
        try:
            await self._notifier(payload)
        except Exception:
            logger.warning(LOG_RELAY_FAILED, project_id=project_id, exc_info=True)


async def deliver(project_id: str, event: Event, refetch: GateRefetch) -> None:
    """Mirror the run stage and publish one relayed event into the web's hub."""
    kind = event.get(SSE_PAYLOAD_FIELD_EVENT)
    if kind == SSE_EVENT_RUN_STAGE_CHANGED:
        set_run_stage(project_id, str(event.get(SSE_PAYLOAD_FIELD_RUN_STAGE, "")))
    if kind == SSE_EVENT_RUN_FINISHED:
        clear_run_stage(project_id)
    if event.get(FIELD_REFETCH):
        rebuilt = await refetch(project_id)
        if rebuilt is None:
            return
        event = rebuilt
    await get_workflow_sse_hub().publish(project_id, event)


def gate_refetch(engine_factory: EngineFactory) -> GateRefetch:
    """Rebuild a ``review_required`` event from the checkpoint (web side)."""

    async def refetch(project_id: str) -> Event | None:
        state = await engine_factory().get_workflow_state(project_id)
        if state is None:
            return None
        phase_status = str(state.get("phase_status", ""))
        if phase_status != PHASE_STATUS_AWAITING_HUMAN:
            return None
        return build_review_required_event(
            EventParams(
                project_id=project_id, phase=str(state.get("current_phase", ""))
            ),
            phase_status=phase_status,
            gate_payload=build_review_gate_payload(state),
        )

    return refetch


class ProgressRelayListener:
    """The web side: LISTEN, reconnect after a drop, until stopped."""

    def __init__(self, engine: AsyncEngine, refetch: GateRefetch) -> None:
        self._engine = engine
        self._refetch = refetch
        self._tasks: set[asyncio.Task[None]] = set()

    async def run(self, stop: asyncio.Event) -> None:
        """Listen until ``stop`` is set."""
        while not stop.is_set():
            try:
                await self._listen_once(stop)
            except Exception:
                logger.warning(LOG_RELAY_FAILED, exc_info=True)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=RECONNECT_SECONDS)

    async def _listen_once(self, stop: asyncio.Event) -> None:
        async with asyncpg_connection(self._engine) as connection:
            closed = asyncio.Event()
            connection.add_termination_listener(lambda *_args: closed.set())
            await connection.add_listener(PROGRESS_CHANNEL, self._on_notify)
            waiters = {
                asyncio.ensure_future(stop.wait()),
                asyncio.ensure_future(closed.wait()),
            }
            _, pending = await asyncio.wait(
                waiters, return_when=asyncio.FIRST_COMPLETED
            )
            for waiter in pending:
                waiter.cancel()

    def _on_notify(self, *notification: object) -> None:
        """asyncpg calls this with (connection, pid, channel, payload)."""
        decoded = decode(str(notification[-1]))
        if decoded is None:
            return
        task = asyncio.create_task(deliver(decoded[0], decoded[1], self._refetch))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


__all__ = [
    "ProgressRelayListener",
    "RelayingWorkflowSseHub",
    "decode",
    "deliver",
    "encode",
    "engine_notifier",
    "gate_refetch",
]
