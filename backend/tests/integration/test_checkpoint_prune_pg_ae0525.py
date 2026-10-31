"""Keep-latest, signed-off prune of carousel checkpoints on real Postgres.

Feature: backend/tests/features/checkpoint_prune_ae0525.feature
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from langgraph.types import Command
from sqlalchemy import update

from rag_backend.infrastructure.database import checkpoint_prune
from rag_backend.infrastructure.database.checkpoint_prune import (
    PruneRefusedError,
    apply_prune,
    find_candidates,
)
from rag_backend.infrastructure.database.checkpoint_prune_sql import TableCounts
from rag_backend.infrastructure.database.models import CarouselProjectModel
from rag_backend.modules.autopilot.public import AutopilotRunState
from rag_backend.modules.generation_queue.constants import STATUS_QUEUED
from tests.integration.checkpoint_prune_pg_support import (
    CUTOFF,
    FINISHED_GENERATION,
    HELD_GENERATION,
    OLD,
    RECENT,
    STEPS,
    UNSETTLED,
    database,
    prune_request,
    row_counts,
    seed_autopilot_run,
    seed_carousel,
    seed_generation_run,
    thread_config,
)
from tests.integration.pg_schema_support import requires_postgres


@requires_postgres
async def test_dry_run_lists_matched_threads_and_deletes_nothing() -> None:
    """Scenario: A dry run lists the matched threads and deletes nothing"""
    async with database() as db:
        rejected = await seed_carousel(
            db, status="failed", phase_status="rejected", is_public=False
        )
        published = await seed_carousel(db)
        before = {t: await row_counts(db, t) for t in (rejected, published)}
        found = {c.thread_id: c for c in await find_candidates(db.engine, CUTOFF)}
        assert set(found) == {rejected, published}
        assert found[rejected].phase_status == "rejected"
        assert found[published].is_public is True
        assert found[published].prunable.checkpoints == before[published][0] - 1
        assert {t: await row_counts(db, t) for t in before} == before


@requires_postgres
async def test_only_finished_rejected_or_published_past_ttl_match() -> None:
    """Scenario: Only finished rejected or published carousels past the TTL are matched"""
    async with database() as db:
        await seed_carousel(db, updated_at=RECENT)
        await seed_carousel(db, status="drafting", phase_status="in_progress")
        await seed_carousel(db, needs_republish_since=OLD)
        await seed_carousel(db, is_public=False)
        orphan = str(uuid4())
        await db.graph.ainvoke({"log": []}, config=thread_config(orphan))
        assert await find_candidates(db.engine, CUTOFF) == []


@requires_postgres
async def test_a_carousel_with_an_unsettled_autopilot_run_is_never_matched() -> None:
    """Scenario: A carousel whose autopilot run is queued, running or held is never matched"""
    async with database() as db:
        for state in UNSETTLED:
            await seed_autopilot_run(db, await seed_carousel(db), state)
        settled = await seed_carousel(db)
        await seed_autopilot_run(db, settled, AutopilotRunState.PUBLISHED)
        found = await find_candidates(db.engine, CUTOFF)
        assert [c.thread_id for c in found] == [settled]


@requires_postgres
async def test_a_carousel_with_a_held_generation_run_is_never_matched() -> None:
    """Scenario: A carousel whose generation run is queued, running or held is never matched"""
    async with database() as db:
        for status in HELD_GENERATION:
            await seed_generation_run(db, await seed_carousel(db), status)
        finished = []
        for status in FINISHED_GENERATION:
            project = await seed_carousel(db)
            await seed_generation_run(db, project, status)
            finished.append(project)
        found = await find_candidates(db.engine, CUTOFF)
        assert sorted(c.thread_id for c in found) == sorted(finished)


@requires_postgres
async def test_a_queued_generation_run_after_the_dry_run_stops_the_prune(
    tmp_path: Path,
) -> None:
    """Scenario: A signed-off thread whose carousel gets a queued generation run stops the prune"""
    async with database() as db:
        queued = await seed_carousel(db)
        still = await seed_carousel(db)
        found = {c.thread_id for c in await find_candidates(db.engine, CUTOFF)}
        assert found == {queued, still}
        before = {t: await row_counts(db, t) for t in (queued, still)}
        await seed_generation_run(db, queued, STATUS_QUEUED)
        backup = tmp_path / "b.jsonl"
        with pytest.raises(PruneRefusedError) as refused:
            await apply_prune(db.engine, prune_request((queued, still), backup))
        assert queued in str(refused.value)
        assert still not in str(refused.value)
        assert {t: await row_counts(db, t) for t in before} == before
        assert not backup.exists()


@requires_postgres
async def test_prune_deletes_only_signed_off_threads_and_keeps_a_backup(
    tmp_path: Path,
) -> None:
    """Scenario: The prune deletes only the signed-off threads and keeps a backup"""
    async with database() as db:
        signed = await seed_carousel(db)
        other = await seed_carousel(db)
        other_before = await row_counts(db, other)
        before = await row_counts(db, signed)
        backup = tmp_path / "backup.jsonl"
        deleted = await apply_prune(db.engine, prune_request((signed,), backup))
        after = await row_counts(db, signed)
        assert after[0] == 1
        assert deleted.checkpoints == before[0] - 1
        assert deleted.writes > 0
        assert deleted.blobs > 0
        assert deleted.total == sum(before) - sum(after)
        assert await row_counts(db, other) == other_before
        assert backup.stat().st_mode & 0o777 == 0o600
        lines = [json.loads(line) for line in backup.read_text().splitlines()]
        assert len(lines) == deleted.total
        assert {line["row"]["thread_id"] for line in lines} == {signed}
        tables = [line["table"] for line in lines]
        assert tables.count("checkpoints") == deleted.checkpoints
        assert tables.count("checkpoint_writes") == deleted.writes
        assert tables.count("checkpoint_blobs") == deleted.blobs


@requires_postgres
async def test_a_pruned_thread_keeps_its_workflow_state(tmp_path: Path) -> None:
    """Scenario: A pruned thread keeps its workflow state"""
    async with database() as db:
        thread = await seed_carousel(db)
        before = await db.graph.aget_state(thread_config(thread))
        await apply_prune(db.engine, prune_request((thread,), tmp_path / "b.jsonl"))
        after = await db.graph.aget_state(thread_config(thread))
        assert after.values == before.values
        assert after.next == before.next == ("gate",)
        assert [i.value for i in after.interrupts] == [
            i.value for i in before.interrupts
        ]
        assert before.values["log"] == list(STEPS)


@requires_postgres
async def test_a_pruned_thread_parked_at_a_gate_resumes_to_the_end(
    tmp_path: Path,
) -> None:
    """Scenario: A pruned thread parked at a human gate resumes to the end"""
    async with database() as db:
        thread = await seed_carousel(db)
        deleted = await apply_prune(
            db.engine, prune_request((thread,), tmp_path / "b.jsonl")
        )
        assert deleted.checkpoints > 0
        final = await db.graph.ainvoke(
            Command(resume="ok"), config=thread_config(thread)
        )
        assert final == {"log": list(STEPS), "answer": "ok"}
        state = await db.graph.aget_state(thread_config(thread))
        assert state.next == ()


@requires_postgres
async def test_a_signed_off_thread_no_longer_eligible_stops_the_prune(
    tmp_path: Path,
) -> None:
    """Scenario: A signed-off thread that is no longer eligible stops the prune"""
    async with database() as db:
        resumed = await seed_carousel(db)
        queued = await seed_carousel(db)
        still = await seed_carousel(db)
        before = {t: await row_counts(db, t) for t in (resumed, queued, still)}
        async with db.engine.begin() as conn:
            await conn.execute(
                update(CarouselProjectModel)
                .where(CarouselProjectModel.id == resumed)
                .values(phase_status="in_progress")
            )
        await seed_autopilot_run(db, queued, AutopilotRunState.QUEUED)
        backup = tmp_path / "b.jsonl"
        with pytest.raises(PruneRefusedError) as refused:
            await apply_prune(
                db.engine, prune_request((resumed, queued, still), backup)
            )
        assert resumed in str(refused.value)
        assert queued in str(refused.value)
        assert still not in str(refused.value)
        assert {t: await row_counts(db, t) for t in before} == before
        assert not backup.exists()


@requires_postgres
async def test_a_prune_that_deletes_nothing_is_a_failure(tmp_path: Path) -> None:
    """Scenario: A prune that deletes nothing is reported as a failure"""
    async with database() as db:
        thread = await seed_carousel(db)
        before = await row_counts(db, thread)

        async def deletes_nothing(conn: object, thread_ids: list[str]) -> TableCounts:
            return TableCounts()

        with (
            patch.object(checkpoint_prune, "delete_prunable", deletes_nothing),
            pytest.raises(PruneRefusedError, match="none was deleted"),
        ):
            await apply_prune(db.engine, prune_request((thread,), tmp_path / "b.jsonl"))
        assert await row_counts(db, thread) == before
