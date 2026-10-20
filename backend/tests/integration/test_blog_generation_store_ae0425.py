"""Lease-fenced store + restart reaper on a real database (AE-0425).

Feature: backend/tests/features/blog_generate_ae0425.feature
SQLite here (the JSON-path predicate is portable); CI also runs it on Postgres.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from rag_backend.bootstrap.blog_generation_store import (
    RunOwner,
    SlotWriteGenerationStore,
)
from rag_backend.domain.constants.blog_generation import ERR_GENERATION_INTERRUPTED
from rag_backend.domain.models.blog_document import (
    BlogDocument,
    BlogImage,
    InvalidBlogDocumentError,
    parse_blog_content,
)
from rag_backend.domain.models.blog_generation import (
    DocumentApply,
    GenerationLease,
    GenerationOutcome,
    LeaseLostError,
)
from rag_backend.domain.models.blog_generation_state import (
    GenerationStart,
    generation_of,
    heartbeat,
    started,
)
from rag_backend.infrastructure.database.blog_generation_drafts import (
    GenerationDraftSpec,
    RestartSpec,
    create_generation_draft,
    live_post_id_for_project,
    restart_generation,
)
from rag_backend.infrastructure.database.blog_generation_store import (
    SqlBlogGenerationReaper,
    SqlBlogGenerationStore,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.user import UserModel
from tests.blog_v2_support import v2_content

Sessions = async_sessionmaker[AsyncSession]
AUTHOR_ID = "00000000-0000-4000-8000-0000000a0425"

# asyncpg binds connections to a loop: run the tests on the fixtures' loop.
pytestmark = pytest.mark.asyncio(loop_scope="session")


_PG_URL = os.environ.get("DATABASE_URL", "")
# SQLite always; Postgres too when the gate provides one (CI), in a throwaway
# schema, so the JSON-path lease predicate is proven on both dialects.
_BACKENDS = ["sqlite"] + (["postgres"] if _PG_URL.startswith("postgresql") else [])


async def _sqlite_engine(tmp_path: Path) -> AsyncEngine:
    return create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ae0425.db'}")


@pytest.fixture(params=_BACKENDS)
async def sessions(
    request: pytest.FixtureRequest, tmp_path: Path
) -> AsyncIterator[Sessions]:
    schema = f"ae0425_{uuid.uuid4().hex[:12]}"
    if request.param == "postgres":
        admin = create_async_engine(_PG_URL)
        async with admin.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(
            _PG_URL, connect_args={"server_settings": {"search_path": schema}}
        )
    else:
        admin = None
        engine = await _sqlite_engine(tmp_path)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    makers = async_sessionmaker(engine, expire_on_commit=False)
    async with makers() as db:
        db.add(
            UserModel(
                id=AUTHOR_ID, email="a@ae0425.test", full_name="A", hashed_password="x"
            )
        )
        await db.commit()
    yield makers
    await engine.dispose()
    if admin is not None:
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


def _start(lease: str, now: str | None = None) -> GenerationStart:
    return GenerationStart(
        kind="standalone",
        lease_id=lease,
        now=now or datetime.now(UTC).isoformat(),
        request={"topic": "t"},
    )


async def _draft(
    sessions: Sessions, lease: str = "lease-a", now: str | None = None
) -> GenerationLease:
    async with sessions() as db:
        created = await create_generation_draft(
            db,
            GenerationDraftSpec(
                title="T",
                slug=f"t-{lease}",
                origin="standalone",
                author_id=AUTHOR_ID,
                start=_start(lease, now),
            ),
        )
        await db.commit()
    return created


async def _row(sessions: Sessions, post_id: str) -> BlogPostModel:
    async with sessions() as db:
        row = await db.get(BlogPostModel, post_id)
        assert row is not None
        return row


async def test_draft_row_is_an_in_progress_draft(sessions: Sessions) -> None:
    lease = await _draft(sessions)
    row = await _row(sessions, lease.post_id)
    assert row.status == "draft"
    assert row.content["sections"] == []
    assert generation_of(row.ai_generation_metadata)["status"] == "in_progress"
    assert row.lock_version == 1
    assert row.ai_disclosure_label == "ai_generated"


def _slot_store(sessions: Sessions) -> SlotWriteGenerationStore:
    return SlotWriteGenerationStore(sessions, RunOwner(AUTHOR_ID, image_cap=3))


def _replace_with(body: str) -> DocumentApply:
    document = parse_blog_content(v2_content(body))
    return DocumentApply(edit=lambda _latest: document, voice_score=81.0)


async def test_content_writes_go_through_the_slot_path(sessions: Sessions) -> None:
    # The article write: lease checked on the locked row, voice score
    # mirrored, lock_version bumped. AE-0438 (F-05): the pre-write state is
    # the empty bootstrap, which is never snapshotted — the first version
    # entry appears with the NEXT write and holds the stored article.
    lease = await _draft(sessions)
    store = _slot_store(sessions)
    await store.heartbeat(lease)
    await store.apply_document(lease, _replace_with("Corpo"))
    await store.finish(
        lease, GenerationOutcome(status="complete", image_count=0, title="Novo")
    )
    row = await _row(sessions, lease.post_id)
    assert row.content["sections"][0]["body_md"] == "Corpo"
    assert row.title == "Novo"
    assert row.lock_version == 2
    assert row.ai_generation_metadata["voice_score"] == 81.0
    assert not row.version_history
    assert generation_of(row.ai_generation_metadata)["status"] == "complete"
    await store.apply_document(lease, _replace_with("Corpo 2"))
    row = await _row(sessions, lease.post_id)
    assert [
        entry["snapshot"]["sections"][0]["body_md"]
        for entry in row.version_history
    ] == ["Corpo"]


async def test_a_stale_task_cannot_clobber_a_newer_lease(sessions: Sessions) -> None:
    # Scenario: A stale duplicate task cannot clobber a newer lease
    old = await _draft(sessions)
    store = _slot_store(sessions)
    await store.finish(old, GenerationOutcome(status="failed", recoverable=True))
    async with sessions() as db:
        newer = await restart_generation(
            db, RestartSpec(old.post_id, 1, _start("lease-b"))
        )
        await db.commit()
    assert newer is not None
    await store.apply_document(newer, _replace_with("Lease B"))
    discarded: list[bool] = []
    stale = DocumentApply(
        edit=lambda _latest: parse_blog_content(v2_content("Lease A")),
        images_generated=1,
        discard=lambda: discarded.append(True),
    )
    with pytest.raises(LeaseLostError):
        await store.apply_document(old, stale)
    with pytest.raises(LeaseLostError):
        await store.heartbeat(old)
    assert discarded == [True]  # the stale task's new files are deleted
    row = await _row(sessions, old.post_id)
    assert row.content["sections"][0]["body_md"] == "Lease B"
    assert generation_of(row.ai_generation_metadata)["attempt"] == 2


async def test_images_apply_onto_an_owner_save_and_count(sessions: Sessions) -> None:
    # Review fix 2: an owner save during the image step is the base of the
    # image write (never a conflict); images count against the post's cap.
    lease = await _draft(sessions)
    store = _slot_store(sessions)
    await store.apply_document(lease, _replace_with("Gerado"))
    async with sessions() as db:
        await db.execute(
            update(BlogPostModel).values(
                content=v2_content("Editado pelo dono"),
                lock_version=BlogPostModel.lock_version + 1,
            )
        )
        await db.commit()
    image = BlogImage(url="/api/blog-images/p/x.jpg", alt="Alt")

    def attach(latest: BlogDocument) -> BlogDocument:
        first = latest.sections[0].model_copy(update={"image": image})
        return latest.model_copy(update={"sections": [first]})

    await store.apply_document(lease, DocumentApply(edit=attach, images_generated=2))
    row = await _row(sessions, lease.post_id)
    assert row.content["sections"][0]["body_md"] == "Editado pelo dono"
    assert row.content["sections"][0]["image"]["alt"] == "Alt"
    assert row.lock_version == 4
    # The write itself counts nothing: images are reserved before the spend.
    assert "blog_image_generations" not in row.ai_generation_metadata
    assert await store.read_content(lease) == row.content


async def test_images_are_reserved_up_to_the_cap(sessions: Sessions) -> None:
    # AE-0424 review round 2: reserved under the row lock BEFORE the spend.
    lease = await _draft(sessions)
    store = _slot_store(sessions)
    assert await store.reserve_images(lease, 2) == 2
    assert await store.reserve_images(lease, 5) == 1  # cap 3
    assert await store.reserve_images(lease, 1) == 0
    row = await _row(sessions, lease.post_id)
    assert row.ai_generation_metadata["blog_image_generations"] == 3


async def test_an_invalid_write_is_a_document_error(sessions: Sessions) -> None:
    lease = await _draft(sessions)
    store = _slot_store(sessions)

    def broken(latest: BlogDocument) -> BlogDocument:
        bad = latest.sections[0].model_copy(update={"heading": "# H1 heading"})
        return latest.model_copy(update={"sections": [bad]})

    await store.apply_document(lease, _replace_with("Ok"))
    with pytest.raises(InvalidBlogDocumentError):
        await store.apply_document(lease, DocumentApply(edit=broken))


async def test_the_article_replaces_an_unparseable_row(sessions: Sessions) -> None:
    # Review B: a legacy (non-v2) row cannot be slot-edited; the article
    # write replaces it through the versioned write. AE-0438 (F-05): the
    # legacy pre-write content is not a restorable document either, so no
    # version entry is appended for it.
    lease = await _draft(sessions)
    async with sessions() as db:
        await db.execute(update(BlogPostModel).values(content={"markdown": "# old"}))
        await db.commit()
    store = _slot_store(sessions)
    change = _replace_with("Novo artigo")
    await store.apply_document(
        lease,
        DocumentApply(edit=change.edit, voice_score=80.0, replaces_document=True),
    )
    row = await _row(sessions, lease.post_id)
    assert row.content["sections"][0]["body_md"] == "Novo artigo"
    assert row.ai_generation_metadata["voice_score"] == 80.0
    assert not row.version_history


async def test_a_parseable_row_takes_the_slot_path(sessions: Sessions) -> None:
    lease = await _draft(sessions)
    store = _slot_store(sessions)
    change = _replace_with("Artigo")
    await store.apply_document(
        lease, DocumentApply(edit=change.edit, replaces_document=True)
    )
    row = await _row(sessions, lease.post_id)
    assert row.content["sections"][0]["body_md"] == "Artigo"


async def test_restart_is_compare_and_set(sessions: Sessions) -> None:
    lease = await _draft(sessions)
    async with sessions() as db:
        assert (
            await restart_generation(db, RestartSpec(lease.post_id, 7, _start("x")))
            is None
        )


async def test_a_missing_row_is_a_lost_lease(sessions: Sessions) -> None:
    store = SqlBlogGenerationStore(sessions)
    with pytest.raises(LeaseLostError):
        await store.heartbeat(GenerationLease("missing", "l", 1))


async def test_reaper_fails_stale_runs_and_keeps_partial_content(
    sessions: Sessions,
) -> None:
    # Scenario: A restart mid-generation is reaped to failed/recoverable
    old = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    stale = await _draft(sessions, "stale", now=old)
    fresh = await _draft(sessions, "fresh")
    async with sessions() as db:
        await db.execute(
            update(BlogPostModel)
            .where(BlogPostModel.id == stale.post_id)
            .values(content=v2_content("Parcial"))
        )
        await db.commit()
    async with sessions() as db:
        assert await SqlBlogGenerationReaper(stale_seconds=180).tick(db) == 1
        await db.commit()
    row = await _row(sessions, stale.post_id)
    generation = generation_of(row.ai_generation_metadata)
    assert generation["status"] == "failed"
    assert generation["recoverable"] is True
    errors = generation["errors"]
    assert isinstance(errors, list)
    assert errors[0]["code"] == ERR_GENERATION_INTERRUPTED
    assert row.content["sections"][0]["body_md"] == "Parcial"
    assert (
        generation_of((await _row(sessions, fresh.post_id)).ai_generation_metadata)[
            "status"
        ]
        == "in_progress"
    )
    # The killed run's zombie task can no longer write.
    with pytest.raises(LeaseLostError):
        await SqlBlogGenerationStore(sessions).heartbeat(stale)
    async with sessions() as db:
        assert await SqlBlogGenerationReaper(stale_seconds=180).tick(db) == 0


async def test_live_row_lookup(sessions: Sessions) -> None:
    async with sessions() as db:
        assert await live_post_id_for_project(db, "nope") is None
    metadata = heartbeat(started({}, _start("z")), "now")
    assert generation_of(metadata)["heartbeat_at"] == "now"


async def test_read_content_is_fenced(sessions: Sessions) -> None:
    store = SqlBlogGenerationStore(sessions)
    with pytest.raises(LeaseLostError):
        await store.read_content(GenerationLease("missing", "l", 1))
