"""The generation queue on a real Postgres: schema one-shot, drive lock, worker loop.

Each test gets a throwaway schema (``search_path``) so the shared test database
and its Alembic gates are never touched.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from pgqueuer import PgQueuer
from pgqueuer.adapters.drivers.asyncpg import AsyncpgDriver
from pgqueuer.adapters.persistence.queries import Queries
from pgqueuer.domain.types import QueueExecutionMode
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.carousel.workflow_sse_hub import (
    get_workflow_sse_hub,
    reset_workflow_sse_hub,
)
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
)
from rag_backend.domain.models.carousel_conflict import CarouselConflictError
from rag_backend.modules.generation_queue.application.dispatcher import (
    Dispatcher,
    DispatcherDependencies,
)
from rag_backend.modules.generation_queue.application.executors import project_key
from rag_backend.modules.generation_queue.application.job_handler import (
    GenerationJobHandler,
    HandlerDependencies,
)
from rag_backend.modules.generation_queue.constants import (
    ENTRYPOINT,
    ERROR_HELD_JOB,
    WORKER_APPLICATION_NAME,
)
from rag_backend.modules.generation_queue.domain.errors import (
    DriveLockBusyError,
    DriveLockLostError,
)
from rag_backend.modules.generation_queue.domain.models import (
    GenerationKind,
    GenerationRun,
    GenerationStatus,
    autopilot_stage,
)
from rag_backend.modules.generation_queue.domain.ports import (
    StepOutcome,
    StepTracker,
)
from rag_backend.modules.generation_queue.infrastructure import schema
from rag_backend.modules.generation_queue.infrastructure.drive_lock import (
    DriveLockTiming,
    PostgresDriveLock,
)
from rag_backend.modules.generation_queue.infrastructure.metrics import (
    read_queue_metrics,
)
from rag_backend.modules.generation_queue.infrastructure.pgq_gateway import (
    PgQueuerJobQueue,
)
from rag_backend.modules.generation_queue.infrastructure.progress_relay import (
    ProgressRelayListener,
    RelayingWorkflowSseHub,
    engine_notifier,
)
from rag_backend.modules.generation_queue.infrastructure.raw_connection import (
    asyncpg_connection,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    SqlGenerationRunStore,
)
from rag_backend.modules.generation_queue.public import hold_project_drive
from rag_backend.worker.main import job_entrypoint
from tests.integration.pg_schema_support import PG_URL, requires_postgres
from tests.unit.modules.generation_queue.queue_fakes import (
    NOW,
    FakeActiveAutopilot,
    FakeNotices,
    FixedClock,
)

pytestmark = [pytest.mark.integration, requires_postgres]

_FAST_LOCK = DriveLockTiming(wait_seconds=0.3, poll_seconds=0.05, watch_seconds=0.05)


@pytest_asyncio.fixture(loop_scope="function")
async def engine() -> AsyncIterator[AsyncEngine]:
    name = f"gq_{uuid4().hex[:12]}"
    admin = create_async_engine(PG_URL)
    async with admin.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{name}"'))
    scoped = create_async_engine(
        PG_URL, connect_args={"server_settings": {"search_path": name}}
    )
    async with scoped.begin() as conn:
        await conn.execute(
            text("CREATE TABLE carousel_projects (id VARCHAR(36) PRIMARY KEY)")
        )
    try:
        yield scoped
    finally:
        await scoped.dispose()
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{name}" CASCADE'))
        await admin.dispose()


async def test_queue_schema_one_shot_is_idempotent(engine: AsyncEngine) -> None:
    """Scenario: The queue schema reaches prod with the deploy"""
    before = await schema.verify(engine)
    assert "generation_runs" in before.missing
    assert "pgqueuer" in before.missing
    applied = await schema.apply(engine)
    assert "generation_runs" in applied.created
    assert applied.pgqueuer == "installed"
    assert (await schema.verify(engine)).missing == ()


async def test_second_queue_schema_run_changes_nothing(engine: AsyncEngine) -> None:
    """Scenario: A second queue schema run changes nothing"""
    await schema.apply(engine)
    again = await schema.apply(engine)
    assert again.created == ()
    assert again.pgqueuer == "upgraded (0 statements)"


async def test_verify_names_missing_pgqueuer_tables(engine: AsyncEngine) -> None:
    """Scenario: Verify fails while a queue object is missing"""
    await schema.apply(engine)
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE pgqueuer_schedules"))
    assert (await schema.verify(engine)).missing == ("pgqueuer_schedules",)


async def test_exactly_one_of_two_drivers_drives(engine: AsyncEngine) -> None:
    """Scenario: Two drivers claim the same project and exactly one drives"""
    lock = PostgresDriveLock(engine, _FAST_LOCK)
    entered = asyncio.Event()
    release = asyncio.Event()
    outcomes: list[str] = []

    async def driver(name: str) -> None:
        try:
            async with lock.hold(["project:p1", "autopilot:r1"]):
                outcomes.append(name)
                entered.set()
                await release.wait()
        except DriveLockBusyError:
            outcomes.append(f"{name}:busy")
            release.set()

    await asyncio.gather(driver("a"), driver("b"))
    assert sorted(outcomes) in (["a", "b:busy"], ["a:busy", "b"])
    async with lock.hold(["project:p1"]):
        outcomes.append("after")
    assert outcomes[-1] == "after"


async def test_losing_the_lock_connection_stops_the_drive(engine: AsyncEngine) -> None:
    """Scenario: Losing the lock connection stops the drive"""
    lock = PostgresDriveLock(engine, _FAST_LOCK)
    with pytest.raises(DriveLockLostError):
        async with lock.hold(["project:p9"]):
            async with engine.connect() as admin:
                await admin.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_locks"
                        " WHERE locktype = 'advisory' AND granted"
                        " AND pid <> pg_backend_pid()"
                    )
                )
                await admin.commit()
            await asyncio.sleep(5)
    async with lock.hold(["project:p9"]):
        pass


@dataclass
class _Recorder:
    """Records starts and ends; fails runs named in ``crash``."""

    running: int = 0
    max_running: int = 0
    order: list[str] = field(default_factory=list)
    crash: set[str] = field(default_factory=set)

    async def lock_keys(self, run: GenerationRun) -> list[str]:
        return [f"run:{run.autopilot_run_id}"]

    async def execute(self, run: GenerationRun, tracker: StepTracker) -> StepOutcome:
        self.running += 1
        self.max_running = max(self.max_running, self.running)
        self.order.append(str(run.autopilot_run_id))
        await tracker.begin("start")
        await asyncio.sleep(0.2)
        self.running -= 1
        if run.autopilot_run_id in self.crash:
            raise ValueError("permanent")
        await tracker.finish("start")
        return StepOutcome.DONE


async def _run_worker(
    engine: AsyncEngine, recorder: _Recorder, run_ids: list[str]
) -> SqlGenerationRunStore:
    await schema.apply(engine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    store = SqlGenerationRunStore(sessions)
    notices = FakeNotices()
    handler = GenerationJobHandler(
        HandlerDependencies(
            store=store,
            lock=PostgresDriveLock(engine, _FAST_LOCK),
            executors={GenerationKind.AUTOPILOT_DRIVE: recorder},
            notices=notices,
            clock=FixedClock(),
            is_provider_error=lambda _exc: False,
        )
    )
    active = FakeActiveAutopilot(runs=[(run_id, None) for run_id in run_ids])
    async with asyncpg_connection(engine) as connection:
        pgq = PgQueuer(AsyncpgDriver(connection))
        pgq.entrypoint(ENTRYPOINT, concurrency_limit=1, on_failure="hold")(
            job_entrypoint(handler)
        )
        dispatcher = Dispatcher(
            DispatcherDependencies(
                store=store,
                queue=PgQueuerJobQueue(Queries(pgq.connection)),
                autopilot=active,
                notices=notices,
            )
        )
        await dispatcher.run_once()
        active.runs.clear()
        await asyncio.wait_for(
            pgq.run(mode=QueueExecutionMode.drain, batch_size=1), timeout=30
        )
        await dispatcher.run_once()
    return store


async def _statuses(
    store: SqlGenerationRunStore, engine: AsyncEngine
) -> dict[str, str]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text("SELECT autopilot_run_id, status, id FROM generation_runs")
        )
        return {str(row[0]): str(row[1]) for row in rows.all()}


async def test_three_runs_generate_one_after_another_in_fifo(
    engine: AsyncEngine,
) -> None:
    """Scenario: Several approved themes are generated one after another"""
    recorder = _Recorder()
    store = await _run_worker(engine, recorder, ["r1", "r2", "r3"])
    assert recorder.order == ["r1", "r2", "r3"]
    assert recorder.max_running == 1
    assert await _statuses(store, engine) == {
        "r1": "succeeded",
        "r2": "succeeded",
        "r3": "succeeded",
    }


async def test_a_permanent_failure_is_held_and_mirrored_once(
    engine: AsyncEngine,
) -> None:
    """Scenario: A held job the handler did not mirror becomes a dead letter"""
    recorder = _Recorder(crash={"r2"})
    store = await _run_worker(engine, recorder, ["r1", "r2"])
    assert await _statuses(store, engine) == {"r1": "succeeded", "r2": "dead_letter"}
    async with engine.connect() as conn:
        held = await conn.scalar(text("SELECT count(*) FROM pgqueuer"))
    assert held == 0


async def test_dispatcher_mirrors_a_job_held_without_the_handler(
    engine: AsyncEngine,
) -> None:
    """Scenario: A held job the handler did not mirror becomes a dead letter"""
    await schema.apply(engine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    store = SqlGenerationRunStore(sessions)
    await store.stage(autopilot_stage("r5"))
    (run,) = await store.undispatched(1)
    notices = FakeNotices()
    async with asyncpg_connection(engine) as connection:
        queries = Queries(AsyncpgDriver(connection))
        queue = PgQueuerJobQueue(queries)
        dispatcher = Dispatcher(
            DispatcherDependencies(
                store=store,
                queue=queue,
                autopilot=FakeActiveAutopilot(),
                notices=notices,
            )
        )
        await dispatcher.run_once()
        job_id = (await store.get(run.id)).pgq_job_id
        await queries.driver.execute(
            "UPDATE pgqueuer SET status = 'failed' WHERE id = $1", job_id
        )
        report = await dispatcher.run_once()
    assert report.dead_lettered == 1
    stored = await store.get(run.id)
    assert stored.status is GenerationStatus.DEAD_LETTER
    assert stored.last_error_code == ERROR_HELD_JOB
    assert notices.staged == [(run.id, ERROR_HELD_JOB)]


async def test_metrics_see_the_worker_connection(engine: AsyncEngine) -> None:
    """Scenario: Queue health is reported and alerts fire once per episode"""
    await schema.apply(engine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    store = SqlGenerationRunStore(sessions, FixedClock())
    await store.stage(autopilot_stage("r1"))
    before = await read_queue_metrics(engine, NOW + timedelta(days=1))
    async with asyncpg_connection(engine) as connection:
        await connection.execute(f"SET application_name = '{WORKER_APPLICATION_NAME}'")
        during = await read_queue_metrics(engine, NOW)
    assert during.worker_connected
    assert during.queued == 1
    assert before.oldest_queued_seconds == int(timedelta(days=1).total_seconds())


async def test_progress_events_cross_processes_through_notify(
    engine: AsyncEngine,
) -> None:
    """Scenario: Progress events reach the web through NOTIFY"""
    reset_workflow_sse_hub()
    received: list[dict[str, object]] = []
    stop = asyncio.Event()

    async def no_refetch(_project_id: str) -> dict[str, object] | None:
        return None

    listener = ProgressRelayListener(engine, no_refetch)
    task = asyncio.create_task(listener.run(stop))

    async def subscribe() -> None:
        async for event in get_workflow_sse_hub().listen("p7", keepalive_seconds=5):
            received.append(event)
            return

    subscriber = asyncio.create_task(subscribe())
    await asyncio.sleep(0.5)
    worker_hub = RelayingWorkflowSseHub(engine_notifier(engine))
    await worker_hub.publish("p7", {"event": "phase_change", "phase": "outline"})
    await asyncio.wait_for(subscriber, timeout=5)
    stop.set()
    await asyncio.wait_for(task, timeout=10)
    reset_workflow_sse_hub()
    assert received == [{"event": "phase_change", "phase": "outline"}]


async def test_dashboard_start_is_refused_while_the_worker_drives(
    engine: AsyncEngine,
) -> None:
    """Scenario: The dashboard start is refused while the worker drives the project"""
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    worker_lock = PostgresDriveLock(engine, _FAST_LOCK)
    async with sessions() as session:
        async with worker_lock.hold([project_key("p3")]):
            with pytest.raises(CarouselConflictError) as raised:
                async with hold_project_drive(session, "p3"):
                    pytest.fail("the start must not drive")
            assert raised.value.conflict.code == CONFLICT_CODE_MUTATION_IN_PROGRESS
        async with hold_project_drive(session, "p3"):
            with pytest.raises(DriveLockBusyError):
                async with worker_lock.hold([project_key("p3")]):
                    pytest.fail("the worker must wait for the start")


async def test_worker_factory_wires_the_queue(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Scenario: Several approved themes are generated one after another"""
    from langgraph.checkpoint.memory import MemorySaver

    from rag_backend.infrastructure.config.settings import Settings
    from rag_backend.worker import main

    async with engine.begin() as conn:
        await conn.run_sync(db_config.Base.metadata.create_all)
    await schema.apply(engine)
    alive = tmp_path / "alive"
    settings = Settings(
        secret_key="s",
        anon_secret_key="a",
        carousel_checkpoint_backend="postgres",
        autopilot_enabled=True,
        generation_worker_alive_file=str(alive),
        workflow_worker_interval_seconds=3600,
    )

    async def memory_checkpointer(*_args: object) -> MemorySaver:
        return MemorySaver()

    def attach(*_args: object) -> AsyncEngine:
        db_config.c_engine = engine
        return engine

    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "init_observability", lambda _settings: None)
    monkeypatch.setattr(main, "attach_db", attach)
    monkeypatch.setattr(main, "build_checkpointer", memory_checkpointer)
    monkeypatch.setattr(main, "close_db", _no_close)
    previous = db_config.c_engine
    try:
        async with main.create_pgqueuer() as pgq:
            assert ENTRYPOINT in pgq.qm.entrypoint_registry
            limit = pgq.qm.entrypoint_registry[ENTRYPOINT].parameters
            assert limit.concurrency_limit == 1
            assert limit.on_failure == "hold"
            for _ in range(50):
                if alive.exists():
                    break
                await asyncio.sleep(0.1)
            assert alive.exists()
            async with engine.connect() as conn:
                names = await conn.scalar(
                    text(
                        "SELECT count(*) FROM pg_stat_activity"
                        " WHERE application_name = :name"
                    ),
                    {"name": WORKER_APPLICATION_NAME},
                )
            assert names == 1
    finally:
        db_config.c_engine = previous
        reset_workflow_sse_hub()


async def _no_close() -> None:
    return None
