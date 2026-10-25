"""Backlog promotion only queues the themes its compare-and-set actually moved.

Feature: backend/tests/features/telegram_queue_flow_ae0523.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from rag_backend.modules.autopilot.application.intake_backlog import IntakeBacklog
from rag_backend.modules.autopilot.domain.backlog import (
    BacklogChange,
    BacklogTheme,
    BacklogWindow,
    GenerateNowCommand,
)
from rag_backend.modules.autopilot.domain.intake import IntakeFacts
from rag_backend.modules.autopilot.domain.ports import QueuedRunCommand

_NOW = datetime(2026, 10, 24, 14, 0, tzinfo=UTC)


@dataclass
class _Backlog:
    themes: list[BacklogTheme]
    taken: set[UUID] = field(default_factory=set)

    async def waiting(self, window: BacklogWindow) -> list[BacklogTheme]:
        del window
        return list(self.themes)

    async def change(self, change: BacklogChange) -> tuple[UUID, ...]:
        return tuple(i for i in change.candidate_ids if i not in self.taken)

    async def unannounced(self) -> list[BacklogTheme]:
        return []

    async def generate_now(self, command: GenerateNowCommand) -> BacklogTheme | None:
        del command
        return None


@dataclass
class _Store:
    queued: list[QueuedRunCommand] = field(default_factory=list)

    async def add_queued_run(self, command: QueuedRunCommand) -> None:
        self.queued.append(command)


def _theme(days: int) -> BacklogTheme:
    return BacklogTheme(
        candidate_id=uuid4(), title=f"{days}", created_at=_NOW - timedelta(days=days)
    )


async def test_a_theme_taken_by_generate_now_gets_no_second_run() -> None:
    """Scenario: A theme taken by "Gerar agora" during the morning intake gets one run"""
    taken, free = _theme(3), _theme(2)
    backlog = _Backlog(themes=[taken, free], taken={taken.candidate_id})
    store = _Store()
    facts = IntakeFacts(
        allowlist=frozenset(),
        known_hashes={},
        carousel_topics=(),
        runs_today=0,
        daily_cap=2,
    )
    promotion = await IntakeBacklog(backlog, store).promote(facts, _NOW)
    assert [c.topic_candidate_id for c in store.queued] == [free.candidate_id]
    assert len(promotion.run_ids) == 1
    assert promotion.waiting_count == 2
