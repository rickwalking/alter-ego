"""Unit tests for the AE-0308 image-provider combo repair script.

Gherkin: tests/features/carousel_image_provider_reroute_ae0308.feature
(scenarios under "Legacy data repair").
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "repair_image_provider_combos.py"
)

_LEGACY_PREVIEW_MODEL = "gemini-2.5-flash-preview-05-20"

_CREATE_TABLE = """
    CREATE TABLE carousel_projects (
        id TEXT PRIMARY KEY,
        image_model TEXT NOT NULL,
        image_style TEXT NOT NULL
    )
"""
_INSERT_ROW = (
    "INSERT INTO carousel_projects (id, image_model, image_style) "
    "VALUES (:id, :model, :style)"
)
_SELECT_ROW = (
    "SELECT image_model, image_style FROM carousel_projects WHERE id = :id"
)


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "repair_image_provider_combos", _SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclass field resolution can find the module.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text(_CREATE_TABLE))
    yield engine
    await engine.dispose()


async def _seed(engine: AsyncEngine, rows: list[tuple[str, str, str]]) -> None:
    from sqlalchemy import text

    async with engine.begin() as conn:
        for row_id, model, style in rows:
            await conn.execute(
                text(_INSERT_ROW), {"id": row_id, "model": model, "style": style}
            )


async def _combo(engine: AsyncEngine, row_id: str) -> tuple[str, str]:
    from sqlalchemy import text

    async with engine.connect() as conn:
        row = (await conn.execute(text(_SELECT_ROW), {"id": row_id})).one()
    return (row[0], row[1])


async def _run_repair(engine: AsyncEngine, dry_run: bool = False):
    script = _load_script()
    async with engine.begin() as conn:
        return await script.repair_image_provider_rows(conn, dry_run=dry_run)


@pytest.mark.unit
class TestNormalizeCombo:
    def test_pre_rename_values_map_to_openai_comic_neon(self) -> None:
        # Scenario: Legacy pre-rename rows are normalized for future re-runs.
        script = _load_script()
        assert script.normalize_combo(_LEGACY_PREVIEW_MODEL, "neon_comic") == (
            "openai",
            "comic_neon",
        )

    def test_gemini_keeps_supported_style(self) -> None:
        # Scenario: Legacy gemini rows keep their style when it is supported.
        script = _load_script()
        assert script.normalize_combo("gemini", "cinematic") == ("openai", "cinematic")

    def test_supported_openai_combo_passes_through(self) -> None:
        # Scenario: Rows already on a supported OpenAI combo are never touched.
        script = _load_script()
        assert script.normalize_combo("openai", "neo_anime") == ("openai", "neo_anime")


@pytest.mark.unit
class TestRepairImageProviderRows:
    @pytest.mark.asyncio
    async def test_repairs_all_legacy_shapes(self, engine: AsyncEngine) -> None:
        await _seed(
            engine,
            [
                ("p1", _LEGACY_PREVIEW_MODEL, "neon_comic"),
                ("p2", "gemini", "cinematic"),
                ("p3", "gemini", "comic_neon"),
                ("p4", "openai", "neo_anime"),
            ],
        )
        repairs = await _run_repair(engine)
        assert {r.project_id for r in repairs} == {"p1", "p2", "p3"}
        assert await _combo(engine, "p1") == ("openai", "comic_neon")
        assert await _combo(engine, "p2") == ("openai", "cinematic")
        assert await _combo(engine, "p3") == ("openai", "comic_neon")
        assert await _combo(engine, "p4") == ("openai", "neo_anime")

    @pytest.mark.asyncio
    async def test_second_run_is_idempotent(self, engine: AsyncEngine) -> None:
        # Scenario: The repair script is idempotent.
        await _seed(engine, [("p1", _LEGACY_PREVIEW_MODEL, "neon_comic")])
        first = await _run_repair(engine)
        second = await _run_repair(engine)
        assert len(first) == 1
        assert second == []
        assert await _combo(engine, "p1") == ("openai", "comic_neon")

    @pytest.mark.asyncio
    async def test_dry_run_reports_without_writing(self, engine: AsyncEngine) -> None:
        await _seed(engine, [("p1", "gemini", "comic_neon")])
        repairs = await _run_repair(engine, dry_run=True)
        assert len(repairs) == 1
        assert await _combo(engine, "p1") == ("gemini", "comic_neon")

    @pytest.mark.asyncio
    async def test_reports_before_and_after_per_row(self, engine: AsyncEngine) -> None:
        # AC: the script logs each row it changes (before → after).
        await _seed(engine, [("p1", _LEGACY_PREVIEW_MODEL, "neon_comic")])
        (repair,) = await _run_repair(engine)
        assert repair.old_model == _LEGACY_PREVIEW_MODEL
        assert repair.old_style == "neon_comic"
        assert repair.new_model == "openai"
        assert repair.new_style == "comic_neon"
