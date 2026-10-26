"""Worker execution of dispatch-only and full maintenance control jobs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rag_backend.modules.generation_queue.application.dispatcher import Dispatcher
from rag_backend.modules.generation_queue.domain.maintenance import (
    MaintenanceOutcome,
    parse_maintenance,
)
from rag_backend.modules.generation_queue.domain.recovery import ScanReport

Promotion = Callable[[], Awaitable[int | None]]
Recovery = Callable[[], Awaitable[ScanReport | None]]


class MaintenanceLock(Protocol):
    """A non-blocking session advisory lock for the complete full pass."""

    def hold(self) -> AbstractAsyncContextManager[bool]:
        """Yield whether this claimant acquired the session lock."""
        ...


@dataclass(frozen=True, kw_only=True)
class MaintenanceDependencies:
    """The existing promotion, recovery and dispatcher paths plus one lock."""

    dispatcher: Dispatcher
    lock: MaintenanceLock
    promotion: Promotion
    recovery: Recovery


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
        return await self._full()

    async def _dispatch(self, run_id: UUID) -> MaintenanceOutcome:
        await self._deps.dispatcher.kick(run_id)
        await self._deps.dispatcher.run_once()
        return MaintenanceOutcome.DISPATCHED

    async def _full(self) -> MaintenanceOutcome:
        async with self._deps.lock.hold() as acquired:
            if not acquired:
                return MaintenanceOutcome.BUSY
            return await self._run_full()

    async def _run_full(self) -> MaintenanceOutcome:
        await self._deps.promotion()
        await self._deps.recovery()
        await self._deps.dispatcher.run_once()
        return MaintenanceOutcome.COMPLETED


__all__ = [
    "MaintenanceDependencies",
    "MaintenanceExecutor",
    "MaintenanceLock",
    "MaintenanceOutcome",
]
