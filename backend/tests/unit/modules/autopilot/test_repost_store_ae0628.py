"""The SQL repost store, the facts cache and the reel-cover claim on SQLite.

Gherkin: tests/features/autopilot_repost_drafts_ae0628.feature,
tests/features/reel_cover_asset_ae0627.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from rag_backend.modules.autopilot.domain.cover_ports import ExpiredCoverQuery
from rag_backend.modules.autopilot.domain.reels import ReelFacts
from rag_backend.modules.autopilot.domain.repost import RepostListQuery
from rag_backend.modules.autopilot.domain.repost_ports import StatusChange
from rag_backend.modules.autopilot.infrastructure.cover_models import (
    AutopilotCoverAssetModel,
)
from rag_backend.modules.autopilot.infrastructure.cover_store import SqlCoverAssetStore
from rag_backend.modules.autopilot.infrastructure.repost_store import SqlRepostStore
from rag_backend.modules.autopilot.repost_constants import (
    STATUS_APPROVED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_PROCESSING,
    STATUS_PUBLISHED,
)
from tests.unit.modules.autopilot.repost_fakes import NOW, stored, window


@pytest.fixture
async def session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    import rag_backend.infrastructure.database.models  # noqa: F401
    from rag_backend.infrastructure.database.config import Base

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'r.db'}", poolclass=NullPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db
    await engine.dispose()


async def test_insert_get_by_key_and_round_trip(session: AsyncSession) -> None:
    store = SqlRepostStore(session)
    await store.lock()
    row = stored(
        window=window(),
        collaborators=("rick",),
        cover_asset_id=uuid4(),
        trim_end_s=30.0,
    )
    await store.insert(row)
    await store.commit()
    got = await store.get(row.id)
    assert got == row
    assert await store.by_key(row.idempotency_key) == row
    assert await store.by_key("missing-key") is None
    assert await store.get(uuid4()) is None


async def test_save_is_compare_and_set(session: AsyncSession) -> None:
    store = SqlRepostStore(session)
    row = stored()
    await store.insert(row)
    approved = replace(
        row,
        status=STATUS_APPROVED,
        publish_at=NOW,
        approved_at=NOW,
        cover_choice="grok",
    )
    assert await store.save(StatusChange(expected=STATUS_PENDING, repost=approved))
    assert not await store.save(StatusChange(expected=STATUS_PENDING, repost=approved))
    got = await store.get(row.id)
    assert (
        got is not None and got.status == STATUS_APPROVED and got.cover_choice == "grok"
    )


async def test_live_since_drafts_since_and_list(session: AsyncSession) -> None:
    store = SqlRepostStore(session)
    recent = stored(created_at=NOW - timedelta(days=2))
    failed = stored(
        created_at=NOW - timedelta(days=1), status=STATUS_FAILED, media_id="2"
    )
    old = stored(created_at=NOW - timedelta(days=100), media_id="3")
    for row in (recent, failed, old):
        await store.insert(row)
    since = NOW - timedelta(days=7)
    assert await store.live_since(recent.media_id, NOW - timedelta(days=90))
    assert not await store.live_since("2", NOW - timedelta(days=90))
    assert await store.drafts_since(since) == 1
    listed = await store.list_reposts(
        RepostListQuery(statuses=(), since=None, limit=10)
    )
    assert [r.id for r in listed] == [failed.id, recent.id, old.id]
    filtered = await store.list_reposts(
        RepostListQuery(statuses=(STATUS_FAILED,), since=since, limit=10)
    )
    assert [r.id for r in filtered] == [failed.id]


async def test_due_and_caption_editing(session: AsyncSession) -> None:
    store = SqlRepostStore(session)
    rows = {
        "render": stored(),
        "expire": stored(preview_ready_at=NOW, expires_at=NOW - timedelta(minutes=1)),
        "waiting": stored(preview_ready_at=NOW, caption_edit_at=NOW),
        "publish": stored(
            status=STATUS_APPROVED, publish_at=NOW - timedelta(minutes=1)
        ),
        "later": stored(status=STATUS_APPROVED, publish_at=NOW + timedelta(hours=1)),
        "poll": stored(status=STATUS_PROCESSING, container_id="c"),
        "done": stored(status=STATUS_PUBLISHED),
    }
    for row in rows.values():
        await store.insert(row)
    due = {r.id for r in await store.due(NOW)}
    assert due == {rows[k].id for k in ("render", "expire", "publish", "poll")}
    editing = await store.caption_editing(NOW - timedelta(minutes=15))
    assert editing is not None and editing.id == rows["waiting"].id
    assert await store.caption_editing(NOW + timedelta(minutes=1)) is None


async def test_latest_and_hidden_media(session: AsyncSession) -> None:
    store = SqlRepostStore(session)
    first = stored(
        media_id="1",
        created_at=NOW - timedelta(days=200),
        status=STATUS_PUBLISHED,
        new_media_id="9",
        published_at=NOW - timedelta(days=199),
    )
    second = stored(media_id="1", created_at=NOW - timedelta(days=5))
    for row in (first, second):
        await store.insert(row)
    latest = await store.latest_for(["1", "2"])
    assert set(latest) == {"1"} and latest["1"].repost_id == second.id
    assert await store.latest_for([]) == {}
    assert await store.hidden_media(NOW - timedelta(days=90)) == frozenset({"1", "9"})
    assert await store.hidden_media(None) == frozenset({"9"})


async def test_facts_cache(session: AsyncSession) -> None:
    store = SqlRepostStore(session)
    facts = ReelFacts(
        media_id="1", duration_s=12.5, collaborators=("rick",), probed_at=NOW
    )
    await store.save_facts(facts)
    await store.save_facts(replace(facts, duration_s=13.0))
    got = await store.facts(["1", "2"])
    assert got["1"].duration_s == 13.0 and got["1"].collaborators == ("rick",)
    assert await store.facts([]) == {}


# Scenario: The sweep keeps a cover a repost claimed
async def test_reel_cover_claim_and_sweep(session: AsyncSession) -> None:
    from rag_backend.infrastructure.database.models.carousel_creator_asset import (
        CarouselCreatorAssetModel,
    )

    asset = CarouselCreatorAssetModel(
        id=str(uuid4()),
        owner_id="owner",
        role="cover",
        content_sha256="a" * 64,
        media_type="image/webp",
        width=1080,
        height=1920,
        relative_path="x.webp",
    )
    session.add(asset)
    await session.flush()
    reel_id, carousel_id = uuid4(), uuid4()
    old = NOW - timedelta(hours=7)
    for cover_id, purpose in ((reel_id, "reel_cover"), (carousel_id, "carousel_cover")):
        session.add(
            AutopilotCoverAssetModel(
                id=cover_id,
                creator_asset_id=asset.id,
                kind="ai_image",
                width=1080,
                height=1920,
                created_at=old,
                purpose=purpose,
            )
        )
    await session.flush()
    covers = SqlCoverAssetStore(session)
    repost_id = uuid4()
    assert not await covers.claim_for_repost(carousel_id, repost_id)
    assert await covers.claim_for_repost(reel_id, repost_id)
    assert not await covers.claim_for_repost(reel_id, uuid4())
    found = await covers.covers_by_ids((reel_id,))
    assert (
        found[reel_id].repost_id == repost_id and found[reel_id].purpose == "reel_cover"
    )
    expired = await covers.expired_covers(ExpiredCoverQuery(before=NOW, limit=10))
    assert [c.asset_id for c in expired] == [carousel_id]
