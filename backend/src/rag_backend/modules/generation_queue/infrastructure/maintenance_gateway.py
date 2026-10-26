"""Durable maintenance enqueue gateways for the worker and web process."""

from __future__ import annotations

from pgqueuer.adapters.drivers.asyncpg import AsyncpgDriver
from pgqueuer.adapters.persistence.queries import Queries
from pgqueuer.domain.types import JobId
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.modules.generation_queue.constants import MAINTENANCE_ENTRYPOINT
from rag_backend.modules.generation_queue.domain.maintenance import (
    MaintenanceCommand,
    MaintenanceEnqueue,
    MaintenanceMode,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    MaintenanceNotice,
)
from rag_backend.modules.generation_queue.infrastructure.raw_connection import (
    asyncpg_connection,
)

_ACTIVE_SQL = (
    "SELECT id FROM {table} WHERE dedupe_key = $1 AND entrypoint = $2"
    " AND status IN ('queued', 'picked') ORDER BY id LIMIT 1"
)
_SCHEDULED_SQL = (
    "SELECT id FROM {table} WHERE entrypoint = $1 AND status = 'queued'"
    " AND dedupe_key IN ($2, $3) ORDER BY id"
)
_ID = "id"
_POSTGRESQL = "postgresql"


class PgQueuerMaintenanceGateway:
    """Insert or find deduped control jobs through PgQueuer ``Queries``."""

    def __init__(self, queries: Queries) -> None:
        self._queries = queries
        self._table = queries.qbe.settings.qualified.queue_table

    async def notify(self, notice: MaintenanceNotice) -> bool:
        """Return whether a dispatch control job was inserted or already active."""
        result = await self.enqueue(MaintenanceCommand(run_id=notice.run_id))
        return result.job_id is not None

    async def request(self, mode: MaintenanceMode) -> MaintenanceEnqueue:
        """Insert or find the active control job for one mode."""
        return await self.enqueue(MaintenanceCommand(mode=mode))

    async def request_full(self) -> MaintenanceEnqueue:
        """Insert or find the shared full control job."""
        return await self.request(MaintenanceMode.FULL)

    async def full_is_active(self) -> bool:
        """Return whether a full pass is queued or picked."""
        return await self._find(MaintenanceCommand()) is not None

    async def supersede_queued_scheduled(self) -> None:
        """Cancel queued promote/scan jobs after a successful full pass."""
        rows = await self._queries.driver.fetch(
            _SCHEDULED_SQL.format(table=self._table),
            MAINTENANCE_ENTRYPOINT,
            MaintenanceMode.PROMOTE.value,
            MaintenanceMode.SCAN.value,
        )
        ids = [JobId(int(str(row[_ID]))) for row in rows]
        if ids:
            await self._queries.mark_job_as_cancelled(ids)

    async def enqueue(self, command: MaintenanceCommand) -> MaintenanceEnqueue:
        """Use PgQueuer's insert trigger and active dedupe index."""
        ids = await self._queries.enqueue(
            MAINTENANCE_ENTRYPOINT,
            command.payload,
            dedupe_key=command.dedupe_key,
            on_conflict="skip",
        )
        first = ids[0] if ids else None
        if first is not None:
            return MaintenanceEnqueue(job_id=int(first), inserted=True)
        return MaintenanceEnqueue(job_id=await self._find(command), inserted=False)

    async def _find(self, command: MaintenanceCommand) -> int | None:
        rows = await self._queries.driver.fetch(
            _ACTIVE_SQL.format(table=self._table),
            command.dedupe_key,
            MAINTENANCE_ENTRYPOINT,
        )
        return int(str(rows[0][_ID])) if rows else None


class WebMaintenanceGateway:
    """Open a short-lived raw asyncpg connection for each durable web request."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def notify(self, notice: MaintenanceNotice) -> bool:
        """Report false off Postgres or when no active control job can be found."""
        result = await self._request(MaintenanceCommand(run_id=notice.run_id))
        return result.job_id is not None

    async def request(self, mode: MaintenanceMode) -> MaintenanceEnqueue:
        """Insert or find a mode-specific job through a short-lived connection."""
        return await self._request(MaintenanceCommand(mode=mode))

    async def request_full(self) -> MaintenanceEnqueue:
        """Return an unavailable result off Postgres for an honest HTTP 503."""
        return await self.request(MaintenanceMode.FULL)

    async def _request(self, command: MaintenanceCommand) -> MaintenanceEnqueue:
        if self._engine.dialect.name != _POSTGRESQL:
            return MaintenanceEnqueue(job_id=None, inserted=False)
        async with asyncpg_connection(self._engine) as connection:
            queries = Queries(AsyncpgDriver(connection))
            return await PgQueuerMaintenanceGateway(queries).enqueue(command)


__all__ = ["PgQueuerMaintenanceGateway", "WebMaintenanceGateway"]
