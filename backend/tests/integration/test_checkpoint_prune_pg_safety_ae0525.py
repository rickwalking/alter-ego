"""The prune's safety nets on real Postgres: restore, subgraphs, refusals.

Feature: backend/tests/features/checkpoint_prune_ae0525.feature
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncConnection

from rag_backend.infrastructure.database import checkpoint_prune, checkpoint_prune_sql
from rag_backend.infrastructure.database.checkpoint_prune import (
    PruneRefusedError,
    apply_prune,
)
from rag_backend.infrastructure.database.checkpoint_prune_backup import restore_backup
from rag_backend.infrastructure.database.checkpoint_prune_sql import TableCounts
from tests.integration.checkpoint_prune_pg_support import (
    database,
    namespace_counts,
    prune_request,
    row_counts,
    seed_carousel,
    snapshot,
    subgraph_flow,
    thread_config,
)
from tests.integration.pg_schema_support import requires_postgres


@requires_postgres
async def test_a_jsonl_backup_restores_every_pruned_row(tmp_path: Path) -> None:
    """Scenario: A JSONL backup restores every pruned row"""
    async with database() as db:
        thread = await seed_carousel(db)
        before = await snapshot(db, thread)
        state = await db.graph.aget_state(thread_config(thread))
        backup = tmp_path / "b.jsonl"
        deleted = await apply_prune(db.engine, prune_request((thread,), backup))
        assert await snapshot(db, thread) != before
        restored = await restore_backup(db.engine, backup)
        assert restored == deleted
        assert await snapshot(db, thread) == before
        after = await db.graph.aget_state(thread_config(thread))
        assert after.values == state.values
        assert after.next == state.next


@requires_postgres
async def test_a_subgraph_namespace_keeps_its_own_latest_checkpoint(
    tmp_path: Path,
) -> None:
    """Scenario: A subgraph namespace keeps its own latest checkpoint"""
    async with database(subgraph_flow) as db:
        thread = await seed_carousel(db)
        config = thread_config(thread)
        namespaces = await namespace_counts(db, thread)
        nested = [ns for ns in namespaces if ns]
        assert nested
        assert all(namespaces[ns] > 1 for ns in namespaces)
        before = await db.graph.aget_state(config, subgraphs=True)
        await apply_prune(db.engine, prune_request((thread,), tmp_path / "b.jsonl"))
        assert await namespace_counts(db, thread) == dict.fromkeys(namespaces, 1)
        after = await db.graph.aget_state(config, subgraphs=True)
        assert after.values == before.values
        assert after.next == before.next == ("review",)
        assert after.tasks[0].state.values == before.tasks[0].state.values
        assert [i.value for i in after.interrupts] == [
            i.value for i in before.interrupts
        ]
        twin = await seed_carousel(db)
        resume = Command(resume="ok")
        final = await db.graph.ainvoke(resume, config=config)
        expected = await db.graph.ainvoke(resume, config=thread_config(twin))
        assert final == expected
        assert final["answer"] == "ok"


@requires_postgres
async def test_a_partial_delete_is_rolled_back(tmp_path: Path) -> None:
    """Scenario: A partial delete or a short backup stops the prune"""
    async with database() as db:
        thread = await seed_carousel(db)
        before = await row_counts(db, thread)
        real_delete = checkpoint_prune_sql.delete_prunable

        async def deletes_one_checkpoint_too_few(
            conn: AsyncConnection, thread_ids: list[str]
        ) -> TableCounts:
            deleted = await real_delete(conn, thread_ids)
            return TableCounts(
                checkpoints=deleted.checkpoints - 1,
                writes=deleted.writes,
                blobs=deleted.blobs,
            )

        with (
            patch.object(
                checkpoint_prune, "delete_prunable", deletes_one_checkpoint_too_few
            ),
            pytest.raises(PruneRefusedError, match="were prunable; rolled back"),
        ):
            await apply_prune(db.engine, prune_request((thread,), tmp_path / "b.jsonl"))
        assert await row_counts(db, thread) == before


@requires_postgres
async def test_a_short_backup_stops_the_prune(tmp_path: Path) -> None:
    """Scenario: A partial delete or a short backup stops the prune"""
    async with database() as db:
        thread = await seed_carousel(db)
        before = await row_counts(db, thread)
        async with db.engine.connect() as conn:
            counts = await checkpoint_prune_sql.prunable_counts(conn, [thread])
        real_rows = checkpoint_prune_sql.prunable_rows

        async def drops_the_last_row(
            conn: AsyncConnection, thread_ids: list[str]
        ) -> list[tuple[str, str]]:
            return (await real_rows(conn, thread_ids))[:-1]

        backup = tmp_path / "b.jsonl"
        with (
            patch.object(checkpoint_prune, "prunable_rows", drops_the_last_row),
            pytest.raises(PruneRefusedError, match="backup holds"),
        ):
            await apply_prune(db.engine, prune_request((thread,), backup))
        assert await row_counts(db, thread) == before
        lines = [json.loads(line) for line in backup.read_text().splitlines()]
        assert len(lines) == counts[thread].total - 1
        assert {line["row"]["thread_id"] for line in lines} == {thread}
