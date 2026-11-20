"""The repost draft service: create, replay, refusals, cover claim, reads.

Gherkin: tests/features/autopilot_repost_drafts_ae0628.feature
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.modules.autopilot.application.repost_drafts import (
    RepostDeps,
    RepostDraftService,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.reels import ReelFacts
from rag_backend.modules.autopilot.domain.repost import RepostError, RepostListQuery
from rag_backend.modules.autopilot.repost_constants import (
    ERR_ALREADY_REPOSTED,
    ERR_ASSET_INVALID,
    ERR_IDEMPOTENCY_CONFLICT,
    ERR_NOT_CONFIGURED,
    ERR_REPOST_NOT_FOUND,
    ERR_UNAVAILABLE,
    ERR_WEEKLY_CAP,
    STATUS_FAILED,
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
    reel_cover,
    stored,
)


def _service(
    store: MemoryStore | None = None,
    reels: FakeReels | None = None,
    covers: FakeCovers | None = None,
) -> tuple[RepostDraftService, MemoryStore, FakeReels, FakeCovers, FakeProbe]:
    store = store or MemoryStore()
    reels = reels if reels is not None else FakeReels(items={MEDIA: reel()})
    covers = covers or FakeCovers()
    probe = FakeProbe()
    service = RepostDraftService(
        RepostDeps(
            store=store,
            covers=covers,
            facts=store,
            reels=reels,
            probe=probe,
            clock=Clock(),
        )
    )
    return service, store, reels, covers, probe


# Scenario: A valid draft is accepted
async def test_valid_draft_is_stored_pending_with_12h_expiry() -> None:
    service, store, _reels, _covers, _probe = _service()
    created = await service.create(draft())
    assert created.status == STATUS_PENDING
    assert created.expires_at == NOW + timedelta(hours=12)
    assert created.permalink == reel().permalink
    assert store.rows[created.id] == created
    assert store.commits == 1 and store.locks == 1


async def test_text_is_cleaned_and_blank_hook_dropped() -> None:
    service, _store, _r, _c, _p = _service()
    created = await service.create(
        draft(
            caption="  legenda\x07 boa ",
            hook_text="   ",
            reason=" motivo bom aqui \x00",
        )
    )
    assert created.caption == "legenda boa"
    assert created.hook_text is None
    assert created.reason == "motivo bom aqui"


# Scenario: The same key and body replay the original response
async def test_same_key_and_body_replay() -> None:
    service, store, _r, _c, _p = _service()
    first = await service.create(draft())
    again = await service.create(draft())
    assert again == first
    assert len(store.rows) == 1


# Scenario: The same key with a different body conflicts
async def test_same_key_different_body_conflicts() -> None:
    service, _store, _r, _c, _p = _service()
    await service.create(draft())
    with pytest.raises(RepostError) as error:
        await service.create(draft(caption="outra legenda"))
    assert (error.value.problem.code, error.value.problem.status) == (
        ERR_IDEMPOTENCY_CONFLICT,
        409,
    )


# Scenario: A Reel with a live repost in 90 days is refused
async def test_live_repost_in_90_days_conflicts() -> None:
    store = MemoryStore()
    old = stored(created_at=NOW - timedelta(days=10))
    store.rows[old.id] = old
    service, *_ = _service(store=store)
    with pytest.raises(RepostError) as error:
        await service.create(draft())
    assert error.value.problem.code == ERR_ALREADY_REPOSTED


async def test_repost_older_than_90_days_or_failed_does_not_block() -> None:
    store = MemoryStore()
    for row in (
        stored(created_at=NOW - timedelta(days=91)),
        stored(created_at=NOW - timedelta(days=1), status=STATUS_FAILED),
    ):
        store.rows[row.id] = row
    service, *_ = _service(store=store)
    assert (await service.create(draft())).status == STATUS_PENDING


# Scenario: The weekly cap
async def test_weekly_cap_counts_non_failed_drafts() -> None:
    store = MemoryStore()
    for media in ("111", "222"):
        row = stored(media_id=media, created_at=NOW - timedelta(days=2))
        store.rows[row.id] = row
    service, *_ = _service(store=store)
    with pytest.raises(RepostError) as error:
        await service.create(draft())
    assert error.value.problem.code == ERR_WEEKLY_CAP


async def test_failed_draft_does_not_count_toward_the_cap() -> None:
    store = MemoryStore()
    for media, status in (("111", STATUS_PENDING), ("222", STATUS_FAILED)):
        row = stored(media_id=media, created_at=NOW - timedelta(days=2), status=status)
        store.rows[row.id] = row
    service, *_ = _service(store=store)
    assert (await service.create(draft())).status == STATUS_PENDING


# Scenario: A cover must be a fresh, unused reel cover
async def test_valid_reel_cover_is_claimed() -> None:
    cover = reel_cover()
    covers = FakeCovers(covers={cover.asset_id: cover})
    service, *_ = _service(covers=covers)
    created = await service.create(draft(cover_asset_id=cover.asset_id))
    assert covers.covers[cover.asset_id].repost_id == created.id


async def test_unknown_cover_is_asset_invalid() -> None:
    service, *_ = _service()
    with pytest.raises(RepostError) as error:
        await service.create(draft(cover_asset_id=uuid4()))
    assert error.value.problem.code == ERR_ASSET_INVALID


async def test_lost_claim_race_is_asset_invalid() -> None:
    cover = reel_cover()

    class _Racing(FakeCovers):
        async def claim_for_repost(self, asset_id: UUID, repost_id: UUID) -> bool:
            return False

    service, store, *_ = _service(covers=_Racing(covers={cover.asset_id: cover}))
    with pytest.raises(RepostError) as error:
        await service.create(draft(cover_asset_id=cover.asset_id))
    assert error.value.problem.code == ERR_ASSET_INVALID
    assert store.commits == 0


# Scenario: Collaborators default to the original Reel's
async def test_collaborators_default_to_the_original() -> None:
    reels = FakeReels(
        items={MEDIA: reel()}, collaborator_names={MEDIA: ("rickwalking13",)}
    )
    service, store, _r, _c, probe = _service(reels=reels)
    created = await service.create(draft())
    assert created.collaborators == ("rickwalking13",)
    assert store.fact_rows[MEDIA].duration_s == 60.0
    assert probe.calls == 1


async def test_explicit_collaborators_and_cached_facts_are_used() -> None:
    store = MemoryStore()
    store.fact_rows[MEDIA] = ReelFacts(
        media_id=MEDIA, duration_s=30.0, collaborators=("cached",), probed_at=NOW
    )
    service, _s, reels, _c, probe = _service(store=store)
    created = await service.create(draft(collaborators=("other",)))
    assert created.collaborators == ("other",)
    assert probe.calls == 0
    assert not any(c.startswith("collab:") for c in reels.calls)


async def test_known_duration_enforces_final_length() -> None:
    store = MemoryStore()
    store.fact_rows[MEDIA] = ReelFacts(
        media_id=MEDIA, duration_s=120.0, collaborators=(), probed_at=NOW
    )
    service, *_ = _service(store=store)
    with pytest.raises(RepostError) as error:
        await service.create(draft())
    assert error.value.problem.field == "trim_end_s"


async def test_collaborator_lookup_failure_reads_as_none() -> None:
    class _NoCollab(FakeReels):
        async def collaborators(self, media_id: str) -> tuple[str, ...]:
            raise InstagramCallError(status_code=500, error_code="x", transient=True)

    service, *_ = _service(reels=_NoCollab(items={MEDIA: reel()}))
    assert (await service.create(draft())).collaborators == ()


async def test_missing_graph_and_graph_failure_are_503() -> None:
    store = MemoryStore()
    service = RepostDraftService(
        RepostDeps(
            store=store,
            covers=FakeCovers(),
            facts=store,
            reels=None,
            probe=None,
            clock=Clock(),
        )
    )
    with pytest.raises(RepostError) as error:
        await service.create(draft())
    assert (error.value.problem.code, error.value.problem.status) == (
        ERR_NOT_CONFIGURED,
        503,
    )
    failing = FakeReels(
        fail=InstagramCallError(status_code=500, error_code="x", transient=True)
    )
    service, *_ = _service(reels=failing)
    with pytest.raises(RepostError) as error:
        await service.create(draft())
    assert error.value.problem.code == ERR_UNAVAILABLE


async def test_unknown_reel_is_not_found() -> None:
    service, *_ = _service(reels=FakeReels())
    with pytest.raises(RepostError) as error:
        await service.create(draft())
    assert error.value.problem.status == 404


# Scenario: A Reel whose video Instagram withholds is refused
async def test_withheld_video_is_refused_without_a_draft() -> None:
    store = MemoryStore()
    reels = FakeReels(items={MEDIA: replace(reel(), video_url=None)})
    service, *_ = _service(store=store, reels=reels)
    with pytest.raises(RepostError) as error:
        await service.create(draft())
    assert (error.value.problem.code, error.value.problem.status) == (
        "source_unavailable",
        422,
    )
    assert store.rows == {} and store.commits == 0


async def test_no_probe_leaves_duration_unknown() -> None:
    store = MemoryStore()
    reels = FakeReels(items={MEDIA: reel()})
    service = RepostDraftService(
        RepostDeps(
            store=store,
            covers=FakeCovers(),
            facts=store,
            reels=reels,
            probe=None,
            clock=Clock(),
        )
    )
    await service.create(draft())
    assert store.fact_rows[MEDIA].duration_s is None


# Scenario: GET /repost/{id} and GET /reposts
async def test_get_and_list() -> None:
    service, store, *_ = _service()
    created = await service.create(draft())
    assert await service.get(created.id) == created
    with pytest.raises(RepostError) as error:
        await service.get(uuid4())
    assert error.value.problem.code == ERR_REPOST_NOT_FOUND
    listed = await service.list(
        RepostListQuery(statuses=(STATUS_PENDING,), since=None, limit=10)
    )
    assert listed == [created]
