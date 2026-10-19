"""Integration tests for the one-shot blog v1 -> v2 cutover command (AE-0423).

Feature: backend/tests/features/blog_sections_ae0423.feature
Runs the real runner and CLI against a file-backed SQLite DB (Postgres-only
``pg_advisory_xact_lock`` is skipped on other dialects).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rag_backend.domain.constants.blog_document import (
    BLOG_SCHEMA_V2,
    BLOG_SECTION_MAX_CHARS,
)
from rag_backend.domain.models.blog_document import parse_blog_content
from rag_backend.infrastructure.database import blog_v2_cutover
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.scripts import blog_v1_to_v2

GPT_MD = (
    "# GPT 5.6 saiu\n\n## O que aconteceu\n\nA OpenAI lançou o GPT 5.6...\n\n"
    "## Por que importa\n\nPara quem desenvolve software, ...\n"
)


@pytest.fixture
async def db(
    tmp_path: Path,
) -> AsyncIterator[tuple[str, async_sessionmaker[AsyncSession]]]:
    url = f"sqlite+aiosqlite:///{tmp_path / 'ae0423.db'}"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield url, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


async def _insert(
    maker: async_sessionmaker[AsyncSession],
    content: object,
    featured: str | None = "https://cdn/old.jpg",
) -> str:
    post_id = str(uuid4())
    async with maker() as session:
        session.add(
            BlogPostModel(
                id=post_id,
                title="GPT 5.6 saiu",
                slug=f"s-{post_id}",
                status="published",
                content=content,
                featured_image_url=featured,
            )
        )
        await session.commit()
    return post_id


async def _row(maker: async_sessionmaker[AsyncSession], post_id: str) -> BlogPostModel:
    async with maker() as session:
        row = (
            await session.execute(
                select(BlogPostModel).where(BlogPostModel.id == post_id)
            )
        ).scalar_one()
        return row


class TestApply:
    # Scenario: A v1 row is cut over in place and the old shape is dropped
    async def test_v1_row_is_rewritten_in_place(self, db) -> None:
        _, maker = db
        post_id = await _insert(maker, {"markdown": GPT_MD})
        before = await _row(maker, post_id)

        report = await blog_v2_cutover.apply(maker)

        row = await _row(maker, post_id)
        content = row.content
        assert content["schema"] == BLOG_SCHEMA_V2
        sections = content["sections"]
        assert isinstance(sections, list)
        assert [s["heading"] for s in sections] == [
            "O que aconteceu",
            "Por que importa",
        ]
        assert all(str(s["id"]).startswith("sec_") for s in sections)
        assert all(s["image"] is None for s in sections)
        assert content["cover"] is None
        assert content["quality"] is None
        assert "markdown" not in content
        assert row.featured_image_url is None
        assert row.updated_at == before.updated_at
        assert report.changed == 1
        assert report.rows[0].cleared_featured_image_url == "https://cdn/old.jpg"
        parse_blog_content(content)

    # Scenario: Every string translation is cut over with the same rules
    async def test_translations_are_rewritten(self, db) -> None:
        _, maker = db
        post_id = await _insert(
            maker,
            {
                "markdown": GPT_MD,
                "translations": {
                    "en": "# Title\n\n## What happened\n\nBody",
                    "es": {"not": "a string"},
                },
            },
        )
        await blog_v2_cutover.apply(maker)
        content = (await _row(maker, post_id)).content
        translations = content["translations"]
        assert isinstance(translations, dict)
        assert set(translations) == {"en"}
        en = translations["en"]
        assert en["schema"] == BLOG_SCHEMA_V2
        assert [(s["heading"], s["body_md"]) for s in en["sections"]] == [
            ("What happened", "Body")
        ]

    # Scenario: An empty or malformed v1 body still yields a valid document
    @pytest.mark.parametrize("content", [None, {}, {"foo": {"bar": 1}}, []])
    async def test_empty_or_malformed_body_yields_one_empty_section(
        self, db, content: object
    ) -> None:
        _, maker = db
        # ``None`` is stored as JSON ``null`` (the column is NOT NULL).
        post_id = await _insert(maker, content)
        await blog_v2_cutover.apply(maker)
        document = parse_blog_content((await _row(maker, post_id)).content)
        assert len(document.sections) == 1
        assert document.sections[0].body_md == ""

    # Scenario: The cutover is idempotent
    async def test_second_apply_changes_nothing(self, db) -> None:
        _, maker = db
        post_id = await _insert(maker, {"markdown": GPT_MD})
        await blog_v2_cutover.apply(maker)
        first = (await _row(maker, post_id)).content

        report = await blog_v2_cutover.apply(maker)

        assert report.changed == 0
        assert report.scanned == 1
        assert (await _row(maker, post_id)).content == first

    async def test_batches_cover_every_row(self, db, monkeypatch) -> None:
        _, maker = db
        monkeypatch.setattr(blog_v2_cutover, "CUTOVER_BATCH_SIZE", 2)
        ids = [await _insert(maker, {"markdown": f"## S{i}\n\nb"}) for i in range(5)]
        report = await blog_v2_cutover.apply(maker)
        assert report.changed == 5
        for post_id in ids:
            assert (await _row(maker, post_id)).content["schema"] == BLOG_SCHEMA_V2

    async def test_oversized_section_is_flagged_not_truncated(self, db) -> None:
        _, maker = db
        body = "x" * (BLOG_SECTION_MAX_CHARS + 5)
        post_id = await _insert(maker, {"markdown": f"## Big\n\n{body}"})
        report = await blog_v2_cutover.apply(maker)
        assert report.rows[0].oversized == ["pt#0"]
        content = (await _row(maker, post_id)).content
        sections = content["sections"]
        assert isinstance(sections, list)
        assert sections[0]["body_md"] == body


class TestDryRun:
    # Scenario: --dry-run reports rows and changes nothing
    async def test_dry_run_reports_counts_and_writes_nothing(self, db) -> None:
        _, maker = db
        original = {
            "markdown": GPT_MD,
            "translations": {"en": "## A\n\nx\n\n## B\n\ny"},
        }
        post_id = await _insert(maker, original)
        report = await blog_v2_cutover.dry_run(maker)

        assert report.changed == 1
        assert report.rows[0].section_counts == {"pt": 2, "en": 2}
        assert (await _row(maker, post_id)).content == original
        lines = blog_v2_cutover.format_report(report)
        assert lines[0].startswith("[dry-run] scanned=1 changed=1")
        assert "sections[pt:2,en:2]" in lines[1]


class TestVerify:
    # Scenario: --verify exits non-zero on a non-v2 row
    async def test_verify_lists_non_v2_rows_and_translations(self, db) -> None:
        _, maker = db
        legacy = await _insert(maker, {"markdown": "x"})
        stray = await _insert(
            maker,
            {"schema": BLOG_SCHEMA_V2, "sections": [], "translations": {"en": "x"}},
        )
        report = await blog_v2_cutover.verify(maker)
        assert sorted(report.non_v2_ids) == sorted([legacy, stray])
        assert any("NOT_V2" in line for line in blog_v2_cutover.format_report(report))

    # Scenario: --verify gates on zero non-v2 rows
    async def test_verify_is_clean_after_apply(self, db) -> None:
        _, maker = db
        await _insert(maker, {"markdown": GPT_MD, "translations": {"en": "## A\n\nx"}})
        await blog_v2_cutover.apply(maker)
        assert (await blog_v2_cutover.verify(maker)).non_v2_ids == []

    async def test_missing_table_is_zero_rows(self, tmp_path: Path) -> None:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'empty.db'}")
        maker = async_sessionmaker(engine, class_=AsyncSession)
        try:
            assert (await blog_v2_cutover.verify(maker)).scanned == 0
            assert (await blog_v2_cutover.apply(maker)).scanned == 0
        finally:
            await engine.dispose()


class TestRollback:
    # Scenario: --rollback re-joins sections to text-equivalent markdown
    async def test_rollback_restores_flat_markdown(self, db) -> None:
        _, maker = db
        en = "## One\n\nBody EN"
        post_id = await _insert(maker, {"markdown": GPT_MD, "translations": {"en": en}})
        await blog_v2_cutover.apply(maker)

        report = await blog_v2_cutover.rollback(maker)

        content = (await _row(maker, post_id)).content
        assert content["markdown"] == (
            "## O que aconteceu\n\nA OpenAI lançou o GPT 5.6...\n\n"
            "## Por que importa\n\nPara quem desenvolve software, ..."
        )
        assert content["translations"] == {"en": en}
        assert "# GPT 5.6 saiu" not in str(content["markdown"])
        assert report.changed == 1
        assert report.rows[0].section_counts == {"pt": 2, "en": 1}
        assert (await blog_v2_cutover.rollback(maker)).changed == 0


class TestCli:
    @pytest.fixture
    def cli_db(self, db, monkeypatch):
        from rag_backend.infrastructure.config.settings import get_settings

        url, maker = db
        monkeypatch.setenv("DATABASE_URL", url)
        get_settings.cache_clear()
        yield maker
        get_settings.cache_clear()
        os.environ.pop("DATABASE_URL", None)

    @pytest.mark.parametrize(
        "argv", [[], ["--dry-run", "--apply"], ["--rollback", "--verify"]]
    )
    def test_invalid_flag_combinations_exit_2(self, argv: list[str]) -> None:
        assert blog_v1_to_v2.main(argv) == blog_v1_to_v2.EXIT_USAGE

    # Scenario: --verify exits non-zero on a non-v2 row
    async def test_verify_exit_codes(self, cli_db, capsys) -> None:
        await _insert(cli_db, {"markdown": "x"})
        args = blog_v1_to_v2.build_parser().parse_args(["--verify"])
        assert await blog_v1_to_v2.run_modes(cli_db, args) == 1
        args = blog_v1_to_v2.build_parser().parse_args(["--apply", "--verify"])
        assert await blog_v1_to_v2.run_modes(cli_db, args) == 0
        out = capsys.readouterr().out
        assert "[apply]" in out
        assert "[verify] scanned=1 changed=0 non_v2=0" in out

    async def test_dry_run_and_rollback_modes(self, cli_db, capsys) -> None:
        await _insert(cli_db, {"markdown": GPT_MD})
        parser = blog_v1_to_v2.build_parser()
        assert (
            await blog_v1_to_v2.run_modes(cli_db, parser.parse_args(["--dry-run"])) == 0
        )
        assert (
            await blog_v1_to_v2.run_modes(cli_db, parser.parse_args(["--apply"])) == 0
        )
        assert (
            await blog_v1_to_v2.run_modes(cli_db, parser.parse_args(["--rollback"]))
            == 0
        )
        out = capsys.readouterr().out
        assert "[dry-run]" in out
        assert "[rollback] scanned=1 changed=1" in out

    def test_main_runs_against_the_configured_database(self, cli_db) -> None:
        # Sync test: ``main`` owns its own event loop via ``asyncio.run``.
        assert blog_v1_to_v2.main(["--verify"]) == 0


class _FakeDialectSession:
    def __init__(self, dialect: str) -> None:
        self._bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect))
        self.executed: list[tuple[str, dict]] = []

    def get_bind(self) -> SimpleNamespace:
        return self._bind

    async def execute(self, statement: object, params: dict | None = None) -> None:
        self.executed.append((str(statement), params or {}))


class TestAdvisoryLock:
    async def test_postgres_batches_take_the_advisory_xact_lock(self) -> None:
        session = _FakeDialectSession("postgresql")
        await blog_v2_cutover._lock(cast(AsyncSession, session))
        assert session.executed == [
            (
                "SELECT pg_advisory_xact_lock(:key)",
                {"key": blog_v2_cutover.CUTOVER_ADVISORY_LOCK_KEY},
            )
        ]

    async def test_other_dialects_skip_the_lock(self) -> None:
        session = _FakeDialectSession("sqlite")
        await blog_v2_cutover._lock(cast(AsyncSession, session))
        assert session.executed == []
