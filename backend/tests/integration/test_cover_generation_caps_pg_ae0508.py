"""The cover generation caps under concurrent starts, on Postgres.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature). Two starts race on separate
sessions; the owner-row lock (``SELECT ... FOR UPDATE``, a no-op on SQLite)
must let exactly one through at the last slot. Skipped without a Postgres
``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.application.services.carousel.cover_generation import (
    CoverGenerationConfig,
    CoverGenerationRefusedError,
    CoverGenerationService,
    StartCoverGeneration,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.cover_generation import ReferencePhoto
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models import (
    CarouselCoverGenerationModel,
    UserModel,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.infrastructure.cover_generations import (
    SqlCoverGenerationRepository,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_ROOT_TABLE = "carousel_cover_generations"


def _with_references(root: str) -> list[str]:
    """``root`` and every table its foreign keys reach, referenced first."""
    ordered: list[str] = []

    def _visit(name: str) -> None:
        if name in ordered:
            return
        for key in Base.metadata.tables[name].foreign_keys:
            target = key.column.table.name
            if target != name:
                _visit(target)
        ordered.append(name)

    _visit(root)
    return ordered


_TABLES = _with_references(_ROOT_TABLE)
_PHOTO = uuid4()


class _Photos:
    async def photo_ids(self, owner_id: str) -> frozenset[UUID]:
        del owner_id
        return frozenset({_PHOTO})

    async def load(self, asset_ids: tuple[UUID, ...]) -> tuple[ReferencePhoto, ...]:
        del asset_ids
        return ()


_BARRIER_SECONDS = 0.5


class _Barrier:
    """Holds each start after it read its usage until both did, or a timeout.

    With the owner-row lock the second start cannot read before the first
    commits, so the first waits out the timeout; without it both read the
    same counts and both would pass.
    """

    def __init__(self) -> None:
        self.arrived = 0
        self.both = asyncio.Event()

    async def wait(self) -> None:
        self.arrived += 1
        if self.arrived >= 2:
            self.both.set()
        try:
            await asyncio.wait_for(self.both.wait(), _BARRIER_SECONDS)
        except TimeoutError:
            return


class _RacingRepository(SqlCoverGenerationRepository):
    """The real repository, paused at the barrier after the usage read."""

    def __init__(self, session: AsyncSession, barrier: _Barrier) -> None:
        super().__init__(session)
        self._barrier = barrier

    async def count_owner_attempts_since(self, owner_id: str, since: datetime) -> int:
        count = await super().count_owner_attempts_since(owner_id, since)
        await self._barrier.wait()
        return count


def _config() -> CoverGenerationConfig:
    return CoverGenerationConfig(
        model="m", cost_usd=0.0, stale_after_seconds=720, now=lambda: datetime.now(UTC)
    )


async def _seed(
    engine: AsyncEngine, done_here: int, done_elsewhere: int
) -> tuple[str, list[str]]:
    """An owner with two POV carousels; ``done_here`` live rows on the first."""
    owner_id, project_ids = str(uuid4()), [str(uuid4()), str(uuid4())]
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add(
            UserModel(
                id=owner_id,
                email=f"{owner_id}@pg.test",
                full_name="Owner",
                hashed_password="x",
                role="editor",
            )
        )
        await session.flush()
        for project_id in project_ids:
            session.add(
                CarouselProjectModel(
                    id=project_id,
                    topic="T",
                    audience="Devs",
                    niche="IA",
                    owner_id=owner_id,
                    content_mode="pov",
                )
            )
        await session.flush()
        now = datetime.now(UTC)
        for index in range(done_here + done_elsewhere):
            session.add(
                CarouselCoverGenerationModel(
                    id=str(uuid4()),
                    project_id=project_ids[0] if index < done_here else None,
                    owner_id=owner_id,
                    status="succeeded",
                    prompt_sha256="0" * 64,
                    photo_count=1,
                    model="m",
                    cost_usd=0.0,
                    created_at=now,
                )
            )
        await session.commit()
    return owner_id, project_ids


def _pov(project_id: str, owner_id: str) -> CarouselProject:
    project = CarouselProject(topic="T", audience="Devs", niche="IA")
    project.id = UUID(project_id)
    project.owner_id = owner_id
    project.content_mode = "pov"
    return project


async def _race(
    engine: AsyncEngine, owner_id: str, project_ids: tuple[str, str]
) -> list[str]:
    """Two concurrent starts (one per given carousel); each outcome."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    barrier = _Barrier()

    async def _start(project_id: str) -> str:
        async with factory() as session:
            service = CoverGenerationService(
                _RacingRepository(session, barrier), _Photos(), _config()
            )
            try:
                run = await service.start(
                    StartCoverGeneration(
                        project=_pov(project_id, owner_id),
                        user_id=owner_id,
                        photo_ids=(_PHOTO,),
                        prompt="no parque",
                        confirmed=True,
                    )
                )
            except CoverGenerationRefusedError as refused:
                return refused.code
            return run.generation.status.value

    return sorted(await asyncio.gather(*(_start(p) for p in project_ids)))


async def _live_rows(engine: AsyncEngine, owner_id: str) -> int:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        repo = SqlCoverGenerationRepository(session)
        return await repo.count_owner_since(owner_id, datetime(2000, 1, 1, tzinfo=UTC))


@requires_postgres
async def test_two_starts_on_a_carousel_at_three_of_four_let_one_through() -> None:
    """Scenario: Two simultaneous starts at the last slot let exactly one through."""
    async with isolated_schema(_TABLES) as engine:
        owner_id, (first, _second) = await _seed(engine, 3, 0)
        outcomes = await _race(engine, owner_id, (first, first))
        live = await _live_rows(engine, owner_id)

    assert outcomes == ["cover_generation_in_progress", "pending"]
    assert live == 4


@requires_postgres
async def test_two_starts_at_thirty_nine_of_forty_let_one_through() -> None:
    """Scenario: Two simultaneous starts at the last slot let exactly one through."""
    async with isolated_schema(_TABLES) as engine:
        owner_id, (first, second) = await _seed(engine, 0, 39)
        outcomes = await _race(engine, owner_id, (first, second))
        live = await _live_rows(engine, owner_id)

    assert outcomes == ["cover_generation_monthly_cap", "pending"]
    assert live == 40
