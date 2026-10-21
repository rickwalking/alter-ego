"""The palette timestamptz one-shot on Postgres (AE-0446, Pedro's decision).

Feature: backend/tests/features/palette_timestamptz_ae0446.feature
"""

from __future__ import annotations

import argparse
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from rag_backend.domain.constants.palette_types import Palette, PaletteMode
from rag_backend.domain.models.palette import CustomPalette
from rag_backend.infrastructure.database import palette_timestamptz
from rag_backend.infrastructure.database.palette_repository import (
    PostgresPaletteRepository,
)
from rag_backend.scripts.palette_timestamptz import (
    EXIT_OK,
    EXIT_VERIFY_FAILED,
    run_modes,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.test_autopilot_migration import ALEMBIC_HEAD, _alembic_config

_REVISION = "e6f7a8b9c0d1"
_PARENT = "d5e6f7a8b9c0"
_TABLE = "palettes"
_COLUMNS = ("created_at", "updated_at")
_NAIVE_UTC = datetime(2026, 6, 1, 12, 30, 0)
_TYPE_SQL = text(
    "SELECT column_name, data_type FROM information_schema.columns"
    " WHERE table_schema = current_schema() AND table_name = 'palettes'"
    " AND column_name IN ('created_at', 'updated_at') ORDER BY column_name"
)


def test_revision_is_the_single_head_on_top_of_the_cover() -> None:
    _command, cfg, script_cls = _alembic_config()
    script = script_cls.from_config(cfg)
    assert list(script.get_heads()) == [ALEMBIC_HEAD] == [_REVISION]
    revision = script.get_revision(_REVISION)
    assert revision is not None
    assert revision.down_revision == _PARENT


def _modes(*, apply: bool, verify: bool) -> argparse.Namespace:
    return argparse.Namespace(apply=apply, verify=verify)


@asynccontextmanager
async def _naive_palettes() -> AsyncIterator[AsyncEngine]:
    """A palettes table shaped like prod today: naive timestamps, one row."""
    async with isolated_schema([_TABLE]) as engine:
        async with engine.begin() as conn:
            for column in _COLUMNS:
                await conn.execute(
                    text(
                        f"ALTER TABLE palettes ALTER COLUMN {column}"
                        f" TYPE timestamp USING {column} AT TIME ZONE 'UTC'"
                    )
                )
            await conn.execute(
                text(
                    'INSERT INTO palettes (id, name, slug, "primary", accent,'
                    " background, mode, keywords, archived, created_at, updated_at)"
                    " VALUES (gen_random_uuid(), 'Old', 'old', '#111111',"
                    " '#222222', '#000000', 'dark', '[]', false, :at, :at)"
                ),
                {"at": _NAIVE_UTC},
            )
        yield engine


async def _column_types(engine: AsyncEngine) -> dict[str, str]:
    async with engine.connect() as conn:
        rows = await conn.execute(_TYPE_SQL)
    return {str(name): str(kind) for name, kind in rows}


def _palette(slug: str, at: datetime) -> CustomPalette:
    return CustomPalette(
        name=slug,
        slug=slug,
        palette=Palette("#112233", "#445566", "#0a0a0a"),
        mode=PaletteMode.DARK,
        created_at=at,
        updated_at=at,
    )


# Scenario: Naive palette timestamps are converted as UTC
@requires_postgres
async def test_apply_converts_naive_columns_keeping_the_utc_instant() -> None:
    async with _naive_palettes() as engine:
        code = await run_modes(engine, _modes(apply=True, verify=True))
        types = await _column_types(engine)
        async with engine.connect() as conn:
            stored = (
                await conn.execute(text("SELECT created_at, updated_at FROM palettes"))
            ).one()

    assert code == EXIT_OK
    assert set(types.values()) == {"timestamp with time zone"}
    expected = _NAIVE_UTC.replace(tzinfo=UTC)
    assert stored.created_at == expected
    assert stored.updated_at == expected


# Scenario: A second run changes nothing
@requires_postgres
async def test_second_apply_is_a_no_op() -> None:
    async with _naive_palettes() as engine:
        first = await palette_timestamptz.apply(engine)
        second = await palette_timestamptz.apply(engine)
        verified = await palette_timestamptz.verify(engine)

    assert first.altered == _COLUMNS
    assert second.altered == ()
    assert verified.still_naive == ()


# Scenario: Verify fails while a column is still naive
@requires_postgres
async def test_verify_only_fails_on_naive_columns() -> None:
    async with _naive_palettes() as engine:
        code = await run_modes(engine, _modes(apply=False, verify=True))
        report = await palette_timestamptz.verify(engine)
        types = await _column_types(engine)

    assert code == EXIT_VERIFY_FAILED
    assert report.still_naive == _COLUMNS
    assert set(types.values()) == {"timestamp without time zone"}
    assert palette_timestamptz.format_report(report)[-1].endswith(
        "STILL NAIVE created_at, updated_at"
    )


@pytest.fixture
def utc_process_tz(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The prod backend container runs in UTC (no TZ is set in the image)."""
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


# Scenario: Palette creates work with naive and aware times after the change
# asyncpg reads a naive value for ``timestamptz`` as the process's local time,
# so main's naive ``utcnow()`` stays correct only in a UTC process (prod); the
# domain now stamps aware UTC, which is correct in any timezone.
@requires_postgres
@pytest.mark.usefixtures("utc_process_tz")
async def test_naive_and_aware_palette_creates_round_trip_after_apply() -> None:
    naive = _palette("naive", datetime(2026, 10, 21, 9, 0, 0))
    aware = _palette("aware", datetime(2026, 10, 21, 9, 0, 0, tzinfo=UTC))
    async with _naive_palettes() as engine:
        await palette_timestamptz.apply(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            repo = PostgresPaletteRepository(session)
            await repo.add(naive)
            await repo.add(aware)
            await session.commit()
        async with factory() as session:
            rows = (
                await session.execute(
                    text("SELECT slug, created_at FROM palettes ORDER BY slug")
                )
            ).all()

    stamps = {str(slug): at for slug, at in rows}
    expected = datetime(2026, 10, 21, 9, 0, 0, tzinfo=UTC)
    assert stamps["aware"] == expected
    assert stamps["naive"] == expected


# Scenario: Palette creates work with naive and aware times after the change
@requires_postgres
async def test_default_palette_stamp_is_aware_utc_in_any_process_timezone() -> None:
    palette = CustomPalette(
        name="Default",
        slug="default",
        palette=Palette("#112233", "#445566", "#0a0a0a"),
        mode=PaletteMode.DARK,
    )
    async with _naive_palettes() as engine:
        await palette_timestamptz.apply(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            stored = await PostgresPaletteRepository(session).add(palette)
            await session.commit()
        async with engine.connect() as conn:
            read = (
                await conn.execute(
                    text("SELECT created_at FROM palettes WHERE slug = 'default'")
                )
            ).scalar_one()

    assert palette.created_at.tzinfo is UTC
    assert stored.created_at == palette.created_at
    assert read == palette.created_at
