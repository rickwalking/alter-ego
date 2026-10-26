"""The dashboard's queue panel: read the board, retry, discard, cancel, generate now.

Every action is a compare-and-set, so a second click (or a Telegram tap on the same
run) answers ``already_resolved``. Retry and discard reuse the Telegram buttons'
revive and discard. Only an autopilot run that has not started can be cancelled:
its queued generation run is cancelled and the run ends as ``failed`` with the
owner's reason. A dashboard resume is never changed here (the editor owns it).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol
from uuid import UUID, uuid4

from rag_backend.modules.autopilot.application.run_revive import (
    ReviveDependencies,
    discard_parked,
)
from rag_backend.modules.autopilot.domain.backlog import (
    BacklogStore,
    BacklogWindow,
    GenerateNowCommand,
    expiry_cutoff,
)
from rag_backend.modules.autopilot.domain.dead_letter import is_dead_letter
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.queue_board import (
    AutopilotFacts,
    BacklogItem,
    BoardInputs,
    GenerationRow,
    QueueBoard,
    build_board,
)
from rag_backend.modules.autopilot.queue_constants import (
    BACKLOG_EXPIRY_DAYS,
    GENERATION_KIND_AUTOPILOT,
    GENERATION_STATUS_DEAD,
    GENERATION_STATUS_RUNNING,
    OUTCOME_ALREADY,
    OUTCOME_DONE,
    OUTCOME_NOT_ALLOWED,
    OUTCOME_NOT_FOUND,
    REASON_OWNER_CANCELLED,
)


@dataclass(frozen=True, kw_only=True)
class GenerationFacts:
    """Kind, status and autopilot run of one generation run."""

    kind: str
    status: str
    autopilot_run_id: str | None


class QueueBoardReader(Protocol):
    """The generation queue as the panel reads and changes it; no commit."""

    async def rows(self) -> list[GenerationRow]:
        """Active runs in FIFO order, then the recent dead letters."""
        ...

    async def facts(self, run_ids: tuple[str, ...]) -> dict[str, AutopilotFacts]:
        """Title and current reason of each autopilot run."""
        ...

    async def drive_minutes(self) -> list[float]:
        """How long the latest finished drives took."""
        ...

    async def generation(self, run_id: UUID) -> GenerationFacts | None:
        """One generation run's facts, or None."""
        ...

    async def theme_exists(self, candidate_id: UUID) -> bool:
        """True when the topic candidate exists."""
        ...

    async def cancel(self, run_id: UUID) -> bool:
        """Cancel a queued or retry-waiting run (compare-and-set)."""
        ...


@dataclass(frozen=True, kw_only=True)
class QueueBoardDependencies:
    """Ports bound to one request's transaction."""

    reader: QueueBoardReader
    backlog: BacklogStore
    revive: ReviveDependencies


class QueueBoardService:
    """Build the panel and apply its buttons."""

    def __init__(self, deps: QueueBoardDependencies) -> None:
        self._deps = deps

    async def board(self) -> QueueBoard:
        """The panel as of now."""
        now = self._deps.revive.clock.now()
        rows = await self._deps.reader.rows()
        run_ids = tuple(
            dict.fromkeys(r.autopilot_run_id for r in rows if r.autopilot_run_id)
        )
        themes = await self._deps.backlog.waiting(
            BacklogWindow(since=expiry_cutoff(now), before=now + timedelta(seconds=1))
        )
        return build_board(
            BoardInputs(
                rows=rows,
                facts=await self._deps.reader.facts(run_ids),
                backlog=[
                    BacklogItem(
                        candidate_id=str(theme.candidate_id),
                        title=theme.title,
                        created_at=theme.created_at,
                        expires_at=theme.created_at
                        + timedelta(days=BACKLOG_EXPIRY_DAYS),
                    )
                    for theme in themes
                ],
                drive_minutes=await self._deps.reader.drive_minutes(),
                now=now,
            )
        )

    async def discard(self, run_id: UUID) -> str:
        """Close a dead-lettered autopilot run."""
        found = await self._parked(run_id)
        if isinstance(found, str):
            return found
        closed = await discard_parked(self._deps.revive, found)
        return OUTCOME_DONE if closed else OUTCOME_ALREADY

    async def cancel(self, run_id: UUID) -> str:
        """Take an autopilot run that has not started out of the queue."""
        facts = await self._deps.reader.generation(run_id)
        run = await self._autopilot_run(facts)
        if facts is None or run is None:
            return OUTCOME_NOT_FOUND if facts is None else OUTCOME_NOT_ALLOWED
        if facts.status == GENERATION_STATUS_RUNNING:
            return OUTCOME_NOT_ALLOWED
        if run.state is not AutopilotRunState.QUEUED:
            return OUTCOME_NOT_ALLOWED
        if not await self._deps.reader.cancel(run_id):
            return OUTCOME_ALREADY
        moved = await self._deps.revive.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=AutopilotRunState.QUEUED,
                new=AutopilotRunState.FAILED,
                reason=REASON_OWNER_CANCELLED,
            )
        )
        return OUTCOME_DONE if moved else OUTCOME_ALREADY

    async def generate_now(self, candidate_id: UUID) -> str:
        """Queue a backlog theme at once, outside the daily cap."""
        if not await self._deps.reader.theme_exists(candidate_id):
            return OUTCOME_NOT_FOUND
        theme = await self._deps.backlog.generate_now(
            GenerateNowCommand(
                candidate_id=candidate_id,
                run_id=uuid4(),
                created_at=self._deps.revive.clock.now(),
            )
        )
        return OUTCOME_DONE if theme is not None else OUTCOME_ALREADY

    async def _parked(self, run_id: UUID) -> AutopilotRun | str:
        facts = await self._deps.reader.generation(run_id)
        if facts is None:
            return OUTCOME_NOT_FOUND
        run = await self._autopilot_run(facts)
        if run is None:
            return OUTCOME_NOT_ALLOWED
        if facts.status != GENERATION_STATUS_DEAD or not is_dead_letter(
            run.state_reason
        ):
            return OUTCOME_ALREADY
        return run

    async def _autopilot_run(
        self, facts: GenerationFacts | None
    ) -> AutopilotRun | None:
        if facts is None or facts.kind != GENERATION_KIND_AUTOPILOT:
            return None
        if not facts.autopilot_run_id:
            return None
        return await self._deps.revive.runs.get(UUID(facts.autopilot_run_id))


__all__ = [
    "GenerationFacts",
    "QueueBoardDependencies",
    "QueueBoardReader",
    "QueueBoardService",
]
