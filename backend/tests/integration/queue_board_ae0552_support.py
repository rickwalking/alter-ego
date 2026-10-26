"""Seed helpers for the queue-board API regressions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from tests.integration.manual_reprocess_support import NOW
from tests.integration.test_queue_board_api_ae0526 import _topic

BOARD = "/api/generation-runs"


async def seed_autopilot(state: str, project_id: str | None, title: str = "") -> UUID:
    """Create one driven autopilot run and its topic."""
    topic_id = await _topic(title=title)
    run_id = uuid4()
    run = AutopilotRunModel(
        id=run_id,
        topic_candidate_id=topic_id,
        carousel_project_id=project_id,
        state=state,
        publish_attempts=0,
        telegram_message_ids=[],
        created_at=NOW,
        updated_at=NOW,
    )
    async with get_session_maker()() as session:
        session.add(run)
        await session.commit()
    return run_id


async def save_rows(rows: list[object]) -> None:
    """Persist test ORM rows in one transaction."""
    async with get_session_maker()() as session:
        for row in rows:
            session.add(row)
        await session.commit()


async def save_generation(row: GenerationRunModel) -> UUID:
    """Persist one generation row and return its durable id."""
    await save_rows([row])
    return row.id


def at(value: str) -> datetime:
    """Parse a response timestamp and normalize SQLite's naive form to UTC."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


__all__ = ["BOARD", "NOW", "at", "save_generation", "save_rows", "seed_autopilot"]
