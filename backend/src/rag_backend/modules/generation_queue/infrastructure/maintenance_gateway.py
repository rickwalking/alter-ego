"""Durable maintenance enqueue gateways for the worker and web process."""

from __future__ import annotations

from pgqueuer.adapters.drivers.asyncpg import AsyncpgDriver
from pgqueuer.adapters.persistence.queries import Queries
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.modules.generation_queue.constants import MAINTENANCE_ENTRYPOINT
from rag_backend.modules.generation_queue.domain.maintenance import (
    MaintenanceCommand,
    MaintenanceEnqueue,
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

    async def request_full(self) -> MaintenanceEnqueue:
        """Insert or find the shared full control job."""
        return await self.enqueue(MaintenanceCommand())

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

    async def request_full(self) -> MaintenanceEnqueue:
        """Return an unavailable result off Postgres for an honest HTTP 503."""
        return await self._request(MaintenanceCommand())

    async def _request(self, command: MaintenanceCommand) -> MaintenanceEnqueue:
        if self._engine.dialect.name != _POSTGRESQL:
            return MaintenanceEnqueue(job_id=None, inserted=False)
        async with asyncpg_connection(self._engine) as connection:
            queries = Queries(AsyncpgDriver(connection))
            return await PgQueuerMaintenanceGateway(queries).enqueue(command)


__all__ = ["PgQueuerMaintenanceGateway", "WebMaintenanceGateway"]
