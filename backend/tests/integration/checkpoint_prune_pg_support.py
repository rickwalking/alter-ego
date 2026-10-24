"""Shared Postgres fixtures of the checkpoint prune integration tests.

A real LangGraph graph checkpointed by ``AsyncPostgresSaver`` in a throwaway
schema, plus carousel projects and autopilot runs to prune against.
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
from urllib.parse import quote
from uuid import uuid4

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from sqlalchemy import func, insert, select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database import checkpoint_prune_sql
from rag_backend.infrastructure.database.checkpoint_prune import PruneRequest
from rag_backend.infrastructure.database.models import CarouselProjectModel
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.public import AutopilotRunState
from tests.integration.pg_schema_support import PG_URL, isolated_schema

TABLES = (
    "users",
    "persona_profiles",
    "quality_rubrics",
    "carousel_creator_assets",
    "carousel_projects",
    "topic_candidates",
    "autopilot_runs",
)
OLD = datetime.now(UTC) - timedelta(days=90)
RECENT = datetime.now(UTC) - timedelta(days=2)
CUTOFF = datetime.now(UTC) - timedelta(days=30)
STEPS = ("research", "outline", "content")
UNSETTLED = (
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
TABLES_BY_ORDER = (
    checkpoint_prune_sql.checkpoints,
    checkpoint_prune_sql.checkpoint_writes,
    checkpoint_prune_sql.checkpoint_blobs,
)

StepResult = dict[str, list[str]]


class FlowState(TypedDict, total=False):
    log: Annotated[list[str], operator.add]
    answer: str


def _step(name: str) -> Callable[[FlowState], StepResult]:
    def run(state: FlowState) -> StepResult:
        return {"log": [name]}

    return run


def _gate(state: FlowState) -> dict[str, str]:
    return {"answer": str(interrupt({"review": state.get("log", [])}))}


def flow_graph(saver: AsyncPostgresSaver) -> CompiledStateGraph[FlowState]:
    graph = StateGraph(FlowState)
    previous = START
    for name in STEPS:
        graph.add_node(name, _step(name))
        graph.add_edge(previous, name)
        previous = name
    graph.add_node("gate", _gate)
    graph.add_edge(previous, "gate")
    graph.add_edge("gate", END)
    return graph.compile(checkpointer=saver)


@dataclass(frozen=True)
class Db:
    engine: AsyncEngine
    saver: AsyncPostgresSaver
    graph: CompiledStateGraph[FlowState]


def _psycopg_url(schema: str) -> str:
    plain = PG_URL.replace("postgresql+asyncpg://", "postgresql://")
    options = quote(f"-csearch_path={schema}")
    return f"{plain}?options={options}"


GraphBuilder = Callable[[AsyncPostgresSaver], CompiledStateGraph[FlowState]]


def subgraph_flow(saver: AsyncPostgresSaver) -> CompiledStateGraph[FlowState]:
    """A parent step, then a subgraph that drafts and parks at its own gate."""
    child = StateGraph(FlowState)
    child.add_node("draft", _step("draft"))
    child.add_node("gate", _gate)
    child.add_edge(START, "draft")
    child.add_edge("draft", "gate")
    child.add_edge("gate", END)
    parent = StateGraph(FlowState)
    parent.add_node("research", _step("research"))
    parent.add_node("review", child.compile())
    parent.add_edge(START, "research")
    parent.add_edge("research", "review")
    parent.add_edge("review", END)
    return parent.compile(checkpointer=saver)


@asynccontextmanager
async def database(build: GraphBuilder = flow_graph) -> AsyncIterator[Db]:
    async with isolated_schema(TABLES) as engine:
        async with engine.connect() as conn:
            schema = str(await conn.scalar(text("SELECT current_schema()")))
        async with AsyncPostgresSaver.from_conn_string(_psycopg_url(schema)) as saver:
            await saver.setup()
            yield Db(engine=engine, saver=saver, graph=build(saver))


def thread_config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}


async def seed_carousel(db: Db, **columns: object) -> str:
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
        "updated_at": OLD,
    }
    values.update(columns)
    async with db.engine.begin() as conn:
        await conn.execute(insert(CarouselProjectModel).values(**values))
    await db.graph.ainvoke({"log": []}, config=thread_config(project_id))
    return project_id


async def seed_autopilot_run(db: Db, project_id: str, state: AutopilotRunState) -> None:
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


async def row_counts(db: Db, thread_id: str) -> tuple[int, int, int]:
    async with db.engine.connect() as conn:
        counts = [
            int(
                await conn.scalar(
                    select(func.count())
                    .select_from(table)
                    .where(table.c.thread_id == thread_id)
                )
                or 0
            )
            for table in TABLES_BY_ORDER
        ]
    return counts[0], counts[1], counts[2]


def prune_request(threads: tuple[str, ...], backup: Path) -> PruneRequest:
    return PruneRequest(thread_ids=threads, cutoff=CUTOFF, backup_path=backup)


async def snapshot(db: Db, thread_id: str) -> dict[str, list[str]]:
    """Every checkpoint row of the thread as sorted JSON, per table."""
    found: dict[str, list[str]] = {}
    async with db.engine.connect() as conn:
        for table in TABLES_BY_ORDER:
            as_json = func.to_jsonb(table.table_valued())
            result = await conn.execute(
                select(as_json).where(table.c.thread_id == thread_id)
            )
            found[table.name] = sorted(
                json.dumps(row, sort_keys=True) for (row,) in result.all()
            )
    return found


async def namespace_counts(db: Db, thread_id: str) -> dict[str, int]:
    """Checkpoints of the thread per namespace."""
    table = checkpoint_prune_sql.checkpoints
    statement = (
        select(table.c.checkpoint_ns, func.count())
        .where(table.c.thread_id == thread_id)
        .group_by(table.c.checkpoint_ns)
    )
    async with db.engine.connect() as conn:
        return {str(ns): int(n) for ns, n in (await conn.execute(statement)).all()}
