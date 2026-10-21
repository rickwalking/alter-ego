"""Integration tests for the AE-0438 blog version fixes (F-05).

Feature: backend/tests/features/blog_versions_errors_ae0438.feature
API: the generation write path never snapshots the empty bootstrap; restoring a
pre-fix empty snapshot 422s with ``blog_version_empty``. CLI: the operator
command counts and repairs empty version-history entries.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.scripts import blog_empty_versions
from tests.blog_v2_support import v2_content, v2_section
from tests.integration.blog_editor_support_ae0424 import (
    BLOG_POSTS_URL,
    SEC_1,
    EditorClients,
    create_post,
    editor_clients,
    get_post,
    if_match,
    put,
    set_fields,
    versions,
)

BOOTSTRAP = {
    "schema": "blog.v2",
    "cover": None,
    "sections": [],
    "translations": {},
    "quality": None,
}

SEC_2 = "sec_00000000-0000-4000-8000-000000000002"


def _history_entry(
    number: int, snapshot: object, title: str = "T"
) -> dict[str, object]:
    return {
        "id": f"e{number}",
        "content_id": "p",
        "content_type": "blog_post",
        "version_number": number,
        "title": title,
        "excerpt": None,
        "snapshot": snapshot,
        "change_summary": "Before save",
        "author_id": "u",
        "created_at": "2026-10-20T00:00:00Z",
    }


def two_sections(first: str, second: str) -> dict[str, object]:
    return {
        "schema": "blog.v2",
        "cover": None,
        "sections": [
            v2_section(first, "Um", SEC_1),
            v2_section(second, "Dois", SEC_2),
        ],
        "translations": {},
        "quality": None,
    }


@pytest.fixture
async def clients(tmp_path: Path) -> AsyncIterator[EditorClients]:
    async with editor_clients(tmp_path) as built:
        yield built


class TestFirstVersionIsTheDraft:
    # Scenario: Generation's first write does not snapshot the empty bootstrap
    async def test_bootstrap_write_appends_nothing(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, two_sections("Original", "Dois"))
        await set_fields(post["id"], content=BOOTSTRAP, version_history=None)
        article = two_sections("Artigo do escritor", "Dois")
        saved = (await put(clients.author, post, {"content": article})).json()
        assert await versions(clients.author, post["id"]) == []

        # Scenario: The first appended version is the first stored AI draft
        edited = two_sections("Artigo editado", "Dois")
        edited_saved = (await put(clients.author, saved, {"content": edited})).json()
        history = await versions(clients.author, post["id"])
        assert [entry["version_number"] for entry in history] == [1]
        assert history[0]["snapshot"] == article
        restored = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/restore-version/1",
            headers=if_match(edited_saved),
        )
        assert restored.status_code == 200, restored.text

    # Scenario: No write ever snapshots an empty document
    async def test_saving_an_empty_document_appends_nothing(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, two_sections("Original", "Dois"))
        saved = (
            await put(clients.author, post, {"content": two_sections("V1", "Dois")})
        ).json()
        await put(clients.author, saved, {"content": v2_content("")})
        history = await versions(clients.author, post["id"])
        assert [entry["version_number"] for entry in history] == [1, 2]
        assert [entry["snapshot"]["sections"][0]["body_md"] for entry in history] == [
            "Original",
            "V1",
        ]
        assert all(entry["snapshot"]["sections"][0]["body_md"] for entry in history)


class TestRestoreOfEmptySnapshot:
    # Scenario: Restoring a pre-fix empty snapshot answers a specific 422
    async def test_pre_fix_empty_version_422s_with_blog_version_empty(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, two_sections("Original", "Dois"))
        saved = (
            await put(clients.author, post, {"content": two_sections("V1", "Dois")})
        ).json()
        await set_fields(
            post["id"],
            version_history=[
                _history_entry(1, BOOTSTRAP),
                _history_entry(2, two_sections("V1", "Dois")),
            ],
        )
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/restore-version/1",
            headers=if_match(saved),
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "blog_version_empty"
        stored = await get_post(clients.author, post["id"])
        assert stored["content"]["sections"][0]["body_md"] == "V1"


@pytest.fixture
async def db(
    tmp_path: Path,
) -> AsyncIterator[tuple[str, async_sessionmaker[AsyncSession]]]:
    url = f"sqlite+aiosqlite:///{tmp_path / 'ae0438.db'}"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield url, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


async def _insert_post(maker: async_sessionmaker[AsyncSession], history: object) -> str:
    post_id = str(uuid4())
    async with maker() as session:
        session.add(
            BlogPostModel(
                id=post_id,
                title="GPT 5.6 saiu",
                slug=f"s-{post_id}",
                status="draft",
                content=v2_content("Corpo"),
                version_history=history,
            )
        )
        await session.commit()
    return post_id


async def _history(maker: async_sessionmaker[AsyncSession], post_id: str) -> object:
    async with maker() as session:
        row = (
            await session.execute(
                select(BlogPostModel.version_history).where(BlogPostModel.id == post_id)
            )
        ).scalar_one()
        return row


class TestOperatorCommand:
    @pytest.fixture
    def cli_db(self, db, monkeypatch):
        from rag_backend.infrastructure.config.settings import get_settings

        url, maker = db
        monkeypatch.setenv("DATABASE_URL", url)
        get_settings.cache_clear()
        yield maker
        get_settings.cache_clear()
        os.environ.pop("DATABASE_URL", None)

    async def test_count_reports_empty_v1_posts_and_writes_nothing(
        self, cli_db, capsys
    ) -> None:
        broken = await _insert_post(
            cli_db,
            [_history_entry(1, BOOTSTRAP), _history_entry(2, v2_content("Artigo"))],
        )
        clean = await _insert_post(cli_db, [_history_entry(1, v2_content("Artigo"))])
        args = blog_empty_versions.build_parser().parse_args(["--count"])
        assert await blog_empty_versions.run_modes(cli_db, args) == 0
        output = capsys.readouterr().out
        assert broken in output
        assert clean not in output
        assert await _history(cli_db, broken) != []

    async def test_apply_drops_empties_and_renumbers_idempotently(
        self, cli_db, capsys
    ) -> None:
        broken = await _insert_post(
            cli_db,
            [
                _history_entry(1, BOOTSTRAP),
                _history_entry(2, v2_content("Artigo")),
                _history_entry(3, v2_content("Edição")),
            ],
        )
        apply = blog_empty_versions.build_parser().parse_args(["--apply"])
        assert await blog_empty_versions.run_modes(cli_db, apply) == 0
        history = await _history(cli_db, broken)
        assert [entry["version_number"] for entry in history] == [1, 2]
        assert history[0]["snapshot"] == v2_content("Artigo")
        assert await blog_empty_versions.run_modes(cli_db, apply) == 0
        output = capsys.readouterr().out
        assert "[apply] scanned=1 changed=0" in output

    async def test_verify_exits_non_zero_while_empties_remain(self, cli_db) -> None:
        await _insert_post(cli_db, [_history_entry(1, BOOTSTRAP)])
        verify = blog_empty_versions.build_parser().parse_args(["--verify"])
        assert await blog_empty_versions.run_modes(cli_db, verify) == 1
        fix = blog_empty_versions.build_parser().parse_args(["--apply", "--verify"])
        assert await blog_empty_versions.run_modes(cli_db, fix) == 0

    def test_no_mode_is_a_usage_error(self) -> None:
        assert blog_empty_versions.main([]) == blog_empty_versions.EXIT_USAGE
