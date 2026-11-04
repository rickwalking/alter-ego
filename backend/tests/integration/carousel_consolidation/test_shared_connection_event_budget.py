"""An event write on this suite's one shared connection is never cancelled.

Feature: carousel_generation_log_ae0556.feature

``test_generation_event_timeout.py`` is the other half: with the real budget in force,
the same slow write is dropped.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from rag_backend.modules.generation_queue.application.generation_events import (
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
    GenerationEventRun,
)
from rag_backend.modules.generation_queue.domain.models import GenerationKind


class _SlowRecorder:
    """A write that outlasts the production budget."""

    async def record(
        self, run: GenerationEventRun, event: GenerationEventInput
    ) -> bool:
        await asyncio.sleep(EVENT_WRITE_TIMEOUT_SECONDS * 2)
        return True


async def test_a_write_slower_than_the_budget_runs_to_the_end() -> None:
    """Scenario: Recorder timeout preserves authoritative generation state"""
    run = GenerationEventRun(
        id=uuid4(),
        kind=GenerationKind.WORKFLOW_RESUME,
        carousel_project_id=str(uuid4()),
    )

    async with generation_event_scope(run, _SlowRecorder()):
        recorded = await record_generation_event(
            GenerationEventInput(event_type=EVENT_RUN_STARTED, outcome=OUTCOME_RUNNING)
        )

    assert recorded is True
