"""Keep-latest, signed-off prune of carousel checkpoints on real Postgres.

Feature: backend/tests/features/checkpoint_prune_ae0525.feature
"""

from __future__ import annotations

import json
import operator
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, TypedDict
from unittest.mock import patch
from urllib.parse import quote
from uuid import uuid4

import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database import checkpoint_prune, checkpoint_prune_sql
from rag_backend.infrastructure.database.checkpoint_prune import (
    PruneRefusedError,
    PruneRequest,
    apply_prune,
    find_candidates,
)
from rag_backend.infrastructure.database.checkpoint_prune_sql import TableCounts
from rag_backend.infrastructure.database.models import CarouselProjectModel
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.public import AutopilotRunState
from tests.integration.pg_schema_support import (
    PG_URL,
    isolated_schema,
    requires_postgres,
)

_TABLES = (
    "users",
    "persona_profiles",
    "quality_rubrics",
    "carousel_creator_assets",
    "carousel_projects",
    "topic_candidates",
    "autopilot_runs",
)
_OLD = datetime.now(UTC) - timedelta(days=90)
_RECENT = datetime.now(UTC) - timedelta(days=2)
_CUTOFF = datetime.now(UTC) - timedelta(days=30)
_STEPS = ("research", "outline", "content")
_UNSETTLED = (
    AutopilotRunState.QUEUED,
    AutopilotRunState.GENERATING,
    AutopilotRunState.AWAITING_OWNER,
    AutopilotRunState.REWORKING,
    AutopilotRunState.SCHEDULED,
    AutopilotRunState.PUBLISHING,
    AutopilotRunState.FAILED,
    AutopilotRunState.ESCALATED,
    AutopilotRunState.PUBLISH_FAILED,
    AutopilotRunState.AWAITING_THESIS,
)
_TABLES_BY_ORDER = (
    checkpoint_prune_sql.checkpoints,
    checkpoint_prune_sql.checkpoint_writes,
    checkpoint_prune_sql.checkpoint_blobs,
)

StepResult = dict[str, list[str]]


class _State(TypedDict, total=False):
    log: Annotated[list[str], operator.add]
    answer: str


def _step(name: str) -> Callable[[_State], StepResult]:
    def run(state: _State) -> StepResult:
        return {"log": [name]}

    return run


def _gate(state: _State) -> dict[str, str]:
    return {"answer": str(interrupt({"review": state.get("log", [])}))}


def _graph(saver: AsyncPostgresSaver) -> CompiledStateGraph[_State]:
    graph = StateGraph(_State)
    previous = START
    for name in _STEPS:
        graph.add_node(name, _step(name))
        graph.add_edge(previous, name)
        previous = name
    graph.add_node("gate", _gate)
    graph.add_edge(previous, "gate")
    graph.add_edge("gate", END)
    return graph.compile(checkpointer=saver)


@dataclass(frozen=True)
class _Db:
    engine: AsyncEngine
    saver: AsyncPostgresSaver
    graph: CompiledStateGraph[_State]


def _psycopg_url(schema: str) -> str:
    plain = PG_URL.replace("postgresql+asyncpg://", "postgresql://")
    options = quote(f"-csearch_path={schema}")
    return f"{plain}?options={options}"


@asynccontextmanager
async def _database() -> AsyncIterator[_Db]:
    async with isolated_schema(_TABLES) as engine:
        async with engine.connect() as conn:
            schema = str(await conn.scalar(text("SELECT current_schema()")))
        async with AsyncPostgresSaver.from_conn_string(_psycopg_url(schema)) as saver:
            await saver.setup()
            yield _Db(engine=engine, saver=saver, graph=_graph(saver))


def _config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}


async def _carousel(db: _Db, **columns: object) -> str:
    project_id = str(uuid4())
    values: dict[str, object] = {
        "id": project_id,
        "topic": "t",
        "niche": "tech",
        "audience": "a",
        "status": "completed",
        "phase_status": "approved",
        "workflow_status": "approved_for_publish",
        "is_public": True,
        "updated_at": _OLD,
    }
    values.update(columns)
    async with db.engine.begin() as conn:
        await conn.execute(insert(CarouselProjectModel).values(**values))
    await db.graph.ainvoke({"log": []}, config=_config(project_id))
    return project_id


async def _autopilot_run(db: _Db, project_id: str, state: AutopilotRunState) -> None:
    topic_id = uuid4()
    async with db.engine.begin() as conn:
        await conn.execute(
            insert(TopicCandidateModel).values(
                id=topic_id,
                title="t",
                angle="a",
                why_viral="w",
                audience="a",
                niche="tech",
                brief="b",
                sources=[],
                score=1,
                signal_hash=topic_id.hex,
                status="used",
            )
        )
        await conn.execute(
            insert(AutopilotRunModel).values(
                id=uuid4(),
                carousel_project_id=project_id,
                topic_candidate_id=topic_id,
                state=state.value,
                telegram_message_ids=[],
            )
        )


async def _rows(db: _Db, thread_id: str) -> tuple[int, int, int]:
    async with db.engine.connect() as conn:
        counts = [
            int(
                await conn.scalar(
                    select(func.count())
                    .select_from(rows)
                    .where(rows.c.thread_id == thread_id)
                )
                or 0
            )
            for rows in _TABLES_BY_ORDER
        ]
    return counts[0], counts[1], counts[2]


def _request(threads: tuple[str, ...], backup: Path) -> PruneRequest:
    return PruneRequest(thread_ids=threads, cutoff=_CUTOFF, backup_path=backup)


@requires_postgres
async def test_dry_run_lists_matched_threads_and_deletes_nothing() -> None:
    """Scenario: A dry run lists the matched threads and deletes nothing"""
    async with _database() as db:
        rejected = await _carousel(
            db, status="failed", phase_status="rejected", is_public=False
        )
        published = await _carousel(db)
        before = {t: await _rows(db, t) for t in (rejected, published)}
        found = {c.thread_id: c for c in await find_candidates(db.engine, _CUTOFF)}
        assert set(found) == {rejected, published}
        assert found[rejected].phase_status == "rejected"
        assert found[published].is_public is True
        assert found[published].prunable.checkpoints == before[published][0] - 1
        assert {t: await _rows(db, t) for t in before} == before


@requires_postgres
async def test_only_finished_rejected_or_published_past_ttl_match() -> None:
    """Scenario: Only finished rejected or published carousels past the TTL are matched"""
    async with _database() as db:
        await _carousel(db, updated_at=_RECENT)
        await _carousel(db, status="drafting", phase_status="in_progress")
        await _carousel(db, needs_republish_since=_OLD)
        await _carousel(db, is_public=False)
        orphan = str(uuid4())
        await db.graph.ainvoke({"log": []}, config=_config(orphan))
        assert await find_candidates(db.engine, _CUTOFF) == []


@requires_postgres
async def test_a_carousel_with_an_unsettled_autopilot_run_is_never_matched() -> None:
    """Scenario: A carousel whose autopilot run is queued, running or held is never matched"""
    async with _database() as db:
        for state in _UNSETTLED:
            await _autopilot_run(db, await _carousel(db), state)
        settled = await _carousel(db)
        await _autopilot_run(db, settled, AutopilotRunState.PUBLISHED)
        found = await find_candidates(db.engine, _CUTOFF)
        assert [c.thread_id for c in found] == [settled]


@requires_postgres
async def test_prune_deletes_only_signed_off_threads_and_keeps_a_backup(
    tmp_path: Path,
) -> None:
    """Scenario: The prune deletes only the signed-off threads and keeps a backup"""
    async with _database() as db:
        signed = await _carousel(db)
        other = await _carousel(db)
        other_before = await _rows(db, other)
        before = await _rows(db, signed)
        backup = tmp_path / "backup.jsonl"
        deleted = await apply_prune(db.engine, _request((signed,), backup))
        after = await _rows(db, signed)
        assert after[0] == 1
        assert deleted.checkpoints == before[0] - 1
        assert deleted.writes > 0
        assert deleted.blobs > 0
        assert deleted.total == sum(before) - sum(after)
        assert await _rows(db, other) == other_before
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
    async with _database() as db:
        thread = await _carousel(db)
        before = await db.graph.aget_state(_config(thread))
        await apply_prune(db.engine, _request((thread,), tmp_path / "b.jsonl"))
        after = await db.graph.aget_state(_config(thread))
        assert after.values == before.values
        assert after.next == before.next == ("gate",)
        assert [i.value for i in after.interrupts] == [
            i.value for i in before.interrupts
        ]
        assert before.values["log"] == list(_STEPS)


@requires_postgres
async def test_a_pruned_thread_parked_at_a_gate_resumes_to_the_end(
    tmp_path: Path,
) -> None:
    """Scenario: A pruned thread parked at a human gate resumes to the end"""
    async with _database() as db:
        thread = await _carousel(db)
        deleted = await apply_prune(
            db.engine, _request((thread,), tmp_path / "b.jsonl")
        )
        assert deleted.checkpoints > 0
        final = await db.graph.ainvoke(Command(resume="ok"), config=_config(thread))
        assert final == {"log": list(_STEPS), "answer": "ok"}
        state = await db.graph.aget_state(_config(thread))
        assert state.next == ()


@requires_postgres
async def test_a_signed_off_thread_no_longer_eligible_stops_the_prune(
    tmp_path: Path,
) -> None:
    """Scenario: A signed-off thread that is no longer eligible stops the prune"""
    async with _database() as db:
        resumed = await _carousel(db)
        queued = await _carousel(db)
        still = await _carousel(db)
        before = {t: await _rows(db, t) for t in (resumed, queued, still)}
        async with db.engine.begin() as conn:
            await conn.execute(
                update(CarouselProjectModel)
                .where(CarouselProjectModel.id == resumed)
                .values(phase_status="in_progress")
            )
        await _autopilot_run(db, queued, AutopilotRunState.QUEUED)
        backup = tmp_path / "b.jsonl"
        with pytest.raises(PruneRefusedError) as refused:
            await apply_prune(db.engine, _request((resumed, queued, still), backup))
        assert resumed in str(refused.value)
        assert queued in str(refused.value)
        assert still not in str(refused.value)
        assert {t: await _rows(db, t) for t in before} == before
        assert not backup.exists()


@requires_postgres
async def test_a_prune_that_deletes_nothing_is_a_failure(tmp_path: Path) -> None:
    """Scenario: A prune that deletes nothing is reported as a failure"""
    async with _database() as db:
        thread = await _carousel(db)
        before = await _rows(db, thread)

        async def deletes_nothing(conn: object, thread_ids: list[str]) -> TableCounts:
            return TableCounts()

        with (
            patch.object(checkpoint_prune, "delete_prunable", deletes_nothing),
            pytest.raises(PruneRefusedError, match="none was deleted"),
        ):
            await apply_prune(db.engine, _request((thread,), tmp_path / "b.jsonl"))
        assert await _rows(db, thread) == before
