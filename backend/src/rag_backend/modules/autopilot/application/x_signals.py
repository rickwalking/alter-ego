"""Store accepted X browser observations and allowlist their URLs.

A batch with only rejections writes nothing. The caller commits once.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import structlog

from rag_backend.modules.autopilot.constants import LOG_X_SIGNALS
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.scout_ports import SaveXSignals, XSignalStore
from rag_backend.modules.autopilot.domain.x_observation import (
    ObservationPlan,
    ObservationRejection,
    ObservedPostInput,
    plan_observations,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class XSignalsDependencies:
    """Collaborators for one intake call."""

    store: XSignalStore
    clock: Clock


@dataclass(frozen=True, kw_only=True)
class XSignalsCommand:
    """The schema-valid posts from one POST."""

    posts: tuple[ObservedPostInput, ...]


@dataclass(frozen=True, kw_only=True)
class XSignalsResult:
    """Canonical URLs stored, and the items the response rejects."""

    accepted: tuple[str, ...]
    rejected: tuple[ObservationRejection, ...]


class XSignalsService:
    """Plan a batch and persist the posts that are still recent status URLs."""

    def __init__(self, deps: XSignalsDependencies) -> None:
        self._deps = deps

    async def accept(self, command: XSignalsCommand) -> XSignalsResult:
        """Store accepted posts and leave rejected ones out of the allowlist."""
        now = self._deps.clock.now()
        plan = plan_observations(command.posts, now)
        await self._persist(plan, now)
        result = _result(plan)
        logger.info(
            LOG_X_SIGNALS,
            accepted=len(result.accepted),
            rejected=len(result.rejected),
        )
        return result

    async def _persist(self, plan: ObservationPlan, stored_at: datetime) -> None:
        if not plan.accepted:
            return
        command = SaveXSignals(rows=plan.accepted, stored_at=stored_at)
        await self._deps.store.save(command)
        await self._deps.store.commit()


def _result(plan: ObservationPlan) -> XSignalsResult:
    accepted = tuple(item.url for item in plan.accepted)
    return XSignalsResult(accepted=accepted, rejected=plan.rejected)
