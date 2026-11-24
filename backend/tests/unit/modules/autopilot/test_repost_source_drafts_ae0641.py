"""Repost drafts that name an uploaded source video, and the source store.

Gherkin: tests/features/autopilot_repost_source_video_ae0641.feature
"""

from __future__ import annotations

import importlib
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from rag_backend.modules.autopilot.api.repost_mapping import draft_from
from rag_backend.modules.autopilot.api.repost_schemas import RepostCreate
from rag_backend.modules.autopilot.application.repost_drafts import (
    RepostDeps,
    RepostDraftService,
)
from rag_backend.modules.autopilot.domain.repost import RepostError, request_hash
from rag_backend.modules.autopilot.domain.repost_source import RepostSource
from rag_backend.modules.autopilot.infrastructure.repost_source_store import (
    SqlRepostSourceStore,
)
from rag_backend.modules.autopilot.repost_constants import (
    ERR_SOURCE_UNAVAILABLE,
    STATUS_PENDING,
)
from tests.unit.modules.autopilot.repost_fakes import (
    MEDIA,
    NOW,
    Clock,
    FakeCovers,
    FakeProbe,
    FakeReels,
    MemoryStore,
    draft,
    reel,
)
from tests.unit.modules.autopilot.repost_source_fakes import (
    HD,
    MemorySources,
    source,
)

_PLAIN_HASH = "ee3f8df0aa3b4bb54b96c8d5fe95d41ec96cbdd9a74e98c9f25432dc1b5a8939"
_INVALID = "source_asset_invalid"


def _service(
    sources: MemorySources | None,
    video_url: str | None = "https://cdn.example/v.mp4",
    probe_seconds: float | None = 60.0,
) -> tuple[RepostDraftService, MemoryStore]:
    store = MemoryStore()
    service = RepostDraftService(
        RepostDeps(
            store=store,
            covers=FakeCovers(),
            facts=store,
            reels=FakeReels(items={MEDIA: replace(reel(), video_url=video_url)}),
            probe=FakeProbe(seconds=probe_seconds),
            clock=Clock(),
            sources=sources,
        )
    )
    return service, store


# Scenario: A draft names the upload as its source
async def test_draft_with_a_fresh_upload_claims_it() -> None:
    upload = source()
    sources = MemorySources(rows={upload.id: upload})
    service, store = _service(sources)
    created = await service.create(draft(source_asset_id=upload.id))
    assert created.status == STATUS_PENDING and created.id in store.rows
    assert sources.rows[upload.id].repost_id == created.id
    assert store.commits == 1


# Scenario: A draft names the upload as its source
async def test_final_length_uses_the_upload_duration() -> None:
    upload = source(probe=replace(HD, duration_s=95.0))
    service, _store = _service(MemorySources(rows={upload.id: upload}))
    with pytest.raises(RepostError) as error:
        await service.create(draft(source_asset_id=upload.id))
    assert error.value.problem.field == "trim_end_s"
    short = source(probe=replace(HD, duration_s=86.0))
    service, _store = _service(
        MemorySources(rows={short.id: short}), probe_seconds=200.0
    )
    created = await service.create(draft(source_asset_id=short.id))
    assert created.status == STATUS_PENDING


# Scenario: An upload makes a Reel without a Graph video repostable
async def test_upload_makes_a_withheld_video_repostable() -> None:
    upload = source()
    service, _store = _service(MemorySources(rows={upload.id: upload}), video_url=None)
    created = await service.create(draft(source_asset_id=upload.id))
    assert created.status == STATUS_PENDING
    plain, _store = _service(MemorySources(), video_url=None)
    with pytest.raises(RepostError) as error:
        await plain.create(draft())
    assert error.value.problem.code == ERR_SOURCE_UNAVAILABLE


# Scenario Outline: A bad source_asset_id is refused
@pytest.mark.parametrize(
    "row",
    [
        None,
        source(repost_id=uuid4()),
        source(created_at=NOW - timedelta(hours=24)),
    ],
)
async def test_bad_source_asset_is_refused(row: RepostSource | None) -> None:
    asset_id = uuid4()
    rows = {} if row is None else {asset_id: replace(row, id=asset_id)}
    service, store = _service(MemorySources(rows=rows))
    with pytest.raises(RepostError) as error:
        await service.create(draft(source_asset_id=asset_id))
    assert error.value.problem.code == _INVALID
    assert error.value.problem.status == 422
    assert store.rows == {}


class _TakenSources(MemorySources):
    async def claim_for_repost(self, asset_id: UUID, repost_id: UUID) -> bool:
        del asset_id, repost_id
        return False


# Scenario Outline: A bad source_asset_id is refused
async def test_a_lost_claim_race_is_refused() -> None:
    upload = source()
    service, store = _service(_TakenSources(rows={upload.id: upload}))
    with pytest.raises(RepostError) as error:
        await service.create(draft(source_asset_id=upload.id))
    assert error.value.problem.code == _INVALID and store.commits == 0


# Scenario Outline: A bad source_asset_id is refused
async def test_without_a_source_store_a_source_is_refused() -> None:
    service, _store = _service(None)
    with pytest.raises(RepostError) as error:
        await service.create(draft(source_asset_id=uuid4()))
    assert error.value.problem.code == _INVALID


# Scenario: The request hash covers the source
def test_request_hash_covers_the_source() -> None:
    plain = draft()
    asset_id = uuid4()
    assert request_hash(plain) == _PLAIN_HASH
    one = request_hash(replace(plain, source_asset_id=asset_id))
    assert one != _PLAIN_HASH
    assert one == request_hash(replace(plain, source_asset_id=asset_id))
    assert one != request_hash(replace(plain, source_asset_id=uuid4()))


# Scenario: A draft names the upload as its source
def test_body_maps_the_source_asset_id() -> None:
    asset_id = uuid4()
    body = {
        "media_id": MEDIA,
        "caption": "Nova legenda",
        "reason": "Views 3x a mediana",
    }
    plain = RepostCreate.model_validate(body)
    named = RepostCreate.model_validate({**body, "source_asset_id": str(asset_id)})
    assert draft_from(plain, "scout-key-0001").source_asset_id is None
    assert draft_from(named, "scout-key-0001").source_asset_id == asset_id


@pytest.fixture
async def session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    importlib.import_module("rag_backend.infrastructure.database.models")
    from rag_backend.infrastructure.database.config import Base

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 's.db'}", poolclass=NullPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db
    await engine.dispose()


# Scenario: A draft names the upload as its source
async def test_sql_store_round_trip_and_claim(session: AsyncSession) -> None:
    store = SqlRepostSourceStore(session)
    upload = source()
    await store.insert(upload)
    await store.commit()
    assert await store.get(upload.id) == upload
    assert await store.get(uuid4()) is None
    repost_id = uuid4()
    assert await store.claim_for_repost(upload.id, repost_id)
    assert not await store.claim_for_repost(upload.id, uuid4())
    await store.commit()
    claimed = await store.for_repost(repost_id)
    assert claimed is not None and claimed.id == upload.id
    assert claimed.repost_id == repost_id
    assert await store.for_repost(uuid4()) is None


# Scenario: Uploads no draft used within 24 hours are swept
async def test_sql_store_lists_and_deletes_old_unused(session: AsyncSession) -> None:
    store = SqlRepostSourceStore(session)
    old = source(created_at=NOW - timedelta(hours=30))
    older = source(created_at=NOW - timedelta(hours=40))
    fresh = source()
    used = source(created_at=NOW - timedelta(hours=30), repost_id=uuid4())
    for item in (old, older, fresh, used):
        await store.insert(item)
    await store.commit()
    stale = await store.unused_before(NOW - timedelta(hours=24))
    assert [item.id for item in stale] == [older.id, old.id]
    await store.delete(old.id)
    await store.commit()
    assert await store.get(old.id) is None
    assert await store.get(fresh.id) is not None
