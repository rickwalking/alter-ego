"""Shared Postgres helpers for reopening an approved carousel's review.

On top of the website cover review harness: a recorded checkpoint reopen
(there is no LangGraph thread in these tests; the graph side is covered by
``tests/unit/agents/test_carousel_review_reopen_ae0597.py``), autopilot runs
with a kept ``scheduled_at``, the real picker and the real due sweep, each on
its own session so they take real row locks.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update

from rag_backend.application.services.carousel.cover_pick import CoverPickCommand
from rag_backend.application.services.carousel.slide_cover_switch import (
    SlideCoverSwitchResult,
)
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.modules.autopilot.bootstrap_schedule import scheduled_publish_sweep
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.editorial.public import (
    CarouselAutomationAcl,
    cover_pick_service,
)
from tests.integration.website_cover_review_pg_support import (
    Harness,
    row,
    seed_run,
    tables,
)


def sweep_tables() -> list[str]:
    """The harness tables plus the slides the publish source reads."""
    return [*tables(), "carousel_slides"]


APPROVED: dict[str, object] = {
    "workflow_status": "approved_for_publish",
    "phase_status": "approved",
}


@dataclass(frozen=True)
class CommittedRow:
    """What another session sees of the carousel row."""

    workflow_status: str
    phase_status: str | None
    hook_asset_id: str | None
    marked: bool
    is_public: bool


async def committed(built: Harness, project_id: str) -> CommittedRow:
    """The row as committed now, read on a fresh session."""
    model = await row(built, project_id)
    return CommittedRow(
        workflow_status=str(model.workflow_status),
        phase_status=model.phase_status,
        hook_asset_id=model.hook_asset_id,
        marked=model.needs_republish_since is not None,
        is_public=bool(model.is_public),
    )


@dataclass
class Checkpoint:
    """A recorded checkpoint reopen; it can pause inside the switch's lock.

    ``seen`` is the committed row each reopen saw (the switch's transaction is
    still open then). With ``proceed`` set, the reopen signals ``entered`` and
    waits, holding the switch's row lock.
    """

    built: Harness
    reopened: list[str] = field(default_factory=list)
    seen: list[CommittedRow] = field(default_factory=list)
    entered: asyncio.Event = field(default_factory=asyncio.Event)
    proceed: asyncio.Event | None = None
    ok: bool = True

    async def reopen(self, project_id: str) -> bool:
        self.reopened.append(project_id)
        self.seen.append(await committed(self.built, project_id))
        self.entered.set()
        if self.proceed is not None:
            await self.proceed.wait()
        return self.ok


class NoOffer:
    """No GrokBot offer for the carousel."""

    async def offer(self, project_id: str) -> SlideCover | None:
        del project_id
        return None


async def pick(
    built: Harness, project_id: str, photo: str, checkpoint: Checkpoint
) -> SlideCoverSwitchResult:
    """The picker (``PUT /cover``) at the seeded lock version."""
    async with built.sessions()() as session:
        project = await CarouselAutomationAcl(session).load_project(project_id)
        assert project is not None
        service = cover_pick_service(session, NoOffer(), checkpoint)
        return await service.pick(
            CoverPickCommand(project=project, asset_id=UUID(photo), expected_version=3)
        )


async def seed_kept_run(
    built: Harness, project_id: str, state: AutopilotRunState, at: datetime
) -> None:
    """An autopilot run in ``state`` that holds ``scheduled_at``."""
    await seed_run(built, project_id, state)
    async with built.sessions()() as session:
        await session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.carousel_project_id == project_id)
            .values(scheduled_at=at)
        )
        await session.commit()


async def age_run(built: Harness, project_id: str, age: timedelta) -> None:
    """Move the run's ``updated_at`` into the past by ``age``."""
    async with built.sessions()() as session:
        await session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.carousel_project_id == project_id)
            .values(updated_at=datetime.now(UTC) - age)
        )
        await session.commit()


@dataclass(frozen=True)
class RunRow:
    """The committed run's state, reason and kept time."""

    state: str
    reason: str | None
    scheduled_at: datetime | None


async def run_row(built: Harness, project_id: str) -> RunRow:
    """The carousel's committed autopilot run."""
    async with built.sessions()() as session:
        model = await session.scalar(
            select(AutopilotRunModel).where(
                AutopilotRunModel.carousel_project_id == project_id
            )
        )
        assert model is not None
        return RunRow(
            state=str(model.state),
            reason=model.state_reason,
            scheduled_at=model.scheduled_at,
        )


async def sweep(built: Harness) -> int:
    """One due tick of the real sweep wiring on its own session."""
    async with built.sessions()() as session:
        return await scheduled_publish_sweep(session, "").tick()


__all__ = [
    "APPROVED",
    "Checkpoint",
    "CommittedRow",
    "NoOffer",
    "RunRow",
    "age_run",
    "committed",
    "pick",
    "run_row",
    "seed_kept_run",
    "sweep",
    "sweep_tables",
]
