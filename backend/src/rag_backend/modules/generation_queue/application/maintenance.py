"""Worker execution of dispatch and mode-specific maintenance control jobs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import structlog

from rag_backend.modules.generation_queue.application.dispatcher import Dispatcher
from rag_backend.modules.generation_queue.constants import LOG_MAINTENANCE_BUSY
from rag_backend.modules.generation_queue.domain.maintenance import (
    MaintenanceMode,
    MaintenanceOutcome,
    parse_maintenance,
)
from rag_backend.modules.generation_queue.domain.recovery import ScanReport

Promotion = Callable[[], Awaitable[int | None]]
Recovery = Callable[[], Awaitable[ScanReport | None]]

logger = structlog.get_logger()


class MaintenanceLock(Protocol):
    """A non-blocking session advisory lock for every maintenance pass."""

    def hold(self) -> AbstractAsyncContextManager[bool]:
        """Yield whether this claimant acquired the session lock."""
        ...


class MaintenanceCoordination(Protocol):
    """Durable full-pass visibility and scheduled-job supersession."""

    async def full_is_active(self) -> bool:
        """Return whether a full pass is queued or picked."""
        ...

    async def supersede_queued_scheduled(self) -> None:
        """Cancel only scheduled jobs that have not started."""
        ...


@dataclass(frozen=True, kw_only=True)
class MaintenanceDependencies:
    """The existing promotion, recovery and dispatcher paths plus one lock."""

    dispatcher: Dispatcher
    lock: MaintenanceLock
    promotion: Promotion
    recovery: Recovery
    coordination: MaintenanceCoordination


class MaintenanceExecutor:
    """Execute only the work named by a durable maintenance payload."""

    def __init__(self, deps: MaintenanceDependencies) -> None:
        self._deps = deps

    async def execute(self, payload: bytes | None) -> MaintenanceOutcome:
        """Run a parsed command, or ignore a foreign payload."""
        command = parse_maintenance(payload)
        if command is None:
            return MaintenanceOutcome.IGNORED
        if command.run_id is not None:
            return await self._dispatch(command.run_id)
        return await self._maintain(command.mode)

    async def _dispatch(self, run_id: UUID) -> MaintenanceOutcome:
        await self._deps.dispatcher.kick(run_id)
        await self._deps.dispatcher.run_once()
        return MaintenanceOutcome.DISPATCHED

    async def _maintain(self, mode: MaintenanceMode) -> MaintenanceOutcome:
        if (
            mode is not MaintenanceMode.FULL
            and await self._deps.coordination.full_is_active()
        ):
            return MaintenanceOutcome.SUBSUMED
        async with self._deps.lock.hold() as acquired:
            if not acquired:
                logger.info(LOG_MAINTENANCE_BUSY, mode=mode.value)
                return MaintenanceOutcome.BUSY
            return await self._run(mode)

    async def _run(self, mode: MaintenanceMode) -> MaintenanceOutcome:
        if mode is MaintenanceMode.PROMOTE:
            await self._deps.promotion()
            return MaintenanceOutcome.COMPLETED
        if mode is MaintenanceMode.SCAN:
            await self._deps.recovery()
            return MaintenanceOutcome.COMPLETED
        return await self._run_full()

    async def _run_full(self) -> MaintenanceOutcome:
        await self._deps.promotion()
        await self._deps.recovery()
        await self._deps.dispatcher.run_once()
        await self._deps.coordination.supersede_queued_scheduled()
        return MaintenanceOutcome.COMPLETED


__all__ = [
    "MaintenanceCoordination",
    "MaintenanceDependencies",
    "MaintenanceExecutor",
    "MaintenanceLock",
    "MaintenanceOutcome",
]
