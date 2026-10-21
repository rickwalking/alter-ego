"""The SQL store + composition of the one-shot EN repair.

Feature: backend/tests/features/blog_generation_en_gate_timeout_ae0435.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rag_backend.application.services.blog.blog_en_repair import BlogEnRepairService
from rag_backend.application.services.blog.blog_translation_service import (
    BlogTranslationService,
)
from rag_backend.bootstrap import blog_en_repair
from rag_backend.domain.models.blog_document import (
    BlogLanguageDocument,
    parse_blog_content,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from tests.blog_v2_support import v2_content

POST_ID = "55555555-5555-4555-8555-555555555555"
PT_BODY = "Todo mundo abre a conversa com o GPT. Eu abro com a fatura de cada tarefa."
EN_BODY = (
    "Everyone opens the conversation with GPT. I open it with the bill of the task."
)

Maker = async_sessionmaker[AsyncSession]


@pytest.fixture
async def maker(tmp_path: Path) -> AsyncIterator[Maker]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'en.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _seed(maker: Maker, author_id: str | None) -> None:
    content = v2_content(PT_BODY)
    content["translations"] = {"en": _language(PT_BODY)}
    async with maker() as db:
        db.add(
            BlogPostModel(
                id=POST_ID,
                title="Título",
                slug="titulo",
                content=content,
                author_id=author_id,
            )
        )
        await db.commit()


def _language(body: str) -> dict[str, object]:
    document = v2_content(body)
    del document["translations"]
    return document


def _english() -> BlogLanguageDocument:
    return BlogLanguageDocument.model_validate(_language(EN_BODY))


class _NoLlm:
    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        return ""


async def test_reads_posts_and_writes_a_versioned_en(maker: Maker) -> None:
    # Scenario: --apply regenerates only the EN of the named post
    await _seed(maker, author_id=None)
    store = blog_en_repair.SqlEnRepairStore(maker)
    assert [post.post_id for post in await store.posts()] == [POST_ID]
    assert await store.post("missing") is None
    await store.replace_english(POST_ID, _english())
    async with maker() as db:
        row = await db.get(BlogPostModel, POST_ID)
        assert row is not None
        document = parse_blog_content(row.content)
        assert document.translations["en"].sections[0].body_md == EN_BODY
        assert document.sections[0].body_md == PT_BODY
        assert row.version_history[-1]["author_id"] == blog_en_repair.EN_REPAIR_ACTOR
        summary = row.version_history[-1]["change_summary"]
        assert summary == blog_en_repair.VERSION_SUMMARY_EN_REPAIR


async def test_the_post_author_is_the_version_author(maker: Maker) -> None:
    await _seed(maker, author_id="user-7")
    await blog_en_repair.SqlEnRepairStore(maker).replace_english(POST_ID, _english())
    async with maker() as db:
        row = await db.get(BlogPostModel, POST_ID)
        assert row is not None
        assert row.version_history[-1]["author_id"] == "user-7"


def test_the_service_uses_the_editor_translation(
    maker: Maker, monkeypatch: pytest.MonkeyPatch
) -> None:
    translator = BlogTranslationService(_NoLlm(), lambda _h, _b: "")
    monkeypatch.setattr(
        blog_en_repair, "build_blog_translation_service", lambda: translator
    )
    service = blog_en_repair.build_en_repair_service(maker)
    assert isinstance(service, BlogEnRepairService)
    assert service._deps.translator is translator
