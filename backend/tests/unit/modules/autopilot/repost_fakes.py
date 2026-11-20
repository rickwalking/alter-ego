"""In-memory fakes for the Reels list and repost tests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from rag_backend.domain.constants.slide_cover import (
    COVER_KIND_AI_IMAGE,
    COVER_PURPOSE_REEL,
)
from rag_backend.modules.autopilot.domain.cover import CoverAsset
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.reels import LastRepost, ReelFacts, ReelMedia
from rag_backend.modules.autopilot.domain.repost import (
    PublishWindow,
    Repost,
    RepostDraft,
    RepostListQuery,
)
from rag_backend.modules.autopilot.domain.repost_ports import StatusChange
from rag_backend.modules.autopilot.repost_constants import (
    CAP_STATUSES,
    LIVE_STATUSES,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_PROCESSING,
)

NOW = datetime(2026, 11, 19, 21, 0, tzinfo=UTC)
MEDIA = "17912345678901234"
VIDEO_URL = "https://cdn.example/v.mp4?oe=6740ABCD"
THUMB_URL = "https://cdn.example/t.jpg"


@dataclass
class Clock:
    """A settable clock."""

    at: datetime = NOW

    def now(self) -> datetime:
        return self.at


def reel(
    media_id: str = MEDIA, days_old: int = 120, product: str = "REELS"
) -> ReelMedia:
    """A Reel published ``days_old`` days before ``NOW``."""
    return ReelMedia(
        media_id=media_id,
        shortcode="DYJJjNlo0-x",
        permalink=f"https://www.instagram.com/reel/{media_id}/",
        product_type=product,
        posted_at=NOW - timedelta(days=days_old),
        caption="original caption",
        video_url=VIDEO_URL,
        thumbnail_url=THUMB_URL,
    )


def draft(**changes: object) -> RepostDraft:
    """A valid draft; ``changes`` override fields."""
    base = RepostDraft(
        media_id=MEDIA,
        caption="Nova legenda #ia #dev",
        hook_text="Sua IA aprova o próprio código ruim.",
        hook_duration_s=2.5,
        trim_start_s=0.0,
        trim_end_s=None,
        cover_asset_id=None,
        collaborators=None,
        share_to_feed=True,
        reason="Views 3x acima da mediana da conta",
        score=1.82,
        window=None,
        idempotency_key="scout-key-0001",
    )
    return replace(base, **changes)


def window(hours_from: int = 1, hours_to: int = 27) -> PublishWindow:
    """A window starting and ending relative to ``NOW``."""
    return PublishWindow(
        earliest=NOW + timedelta(hours=hours_from),
        latest=NOW + timedelta(hours=hours_to),
    )


def stored(**changes: object) -> Repost:
    """A stored pending draft."""
    base = Repost(
        id=uuid4(),
        idempotency_key=f"key-{uuid4().hex[:12]}",
        request_hash="h" * 64,
        media_id=MEDIA,
        status=STATUS_PENDING,
        permalink="https://www.instagram.com/reel/x/",
        caption="Nova legenda",
        hook_text="Gancho",
        hook_duration_s=2.5,
        trim_start_s=0.0,
        trim_end_s=None,
        cover_asset_id=None,
        collaborators=(),
        share_to_feed=True,
        reason="Views 3x acima da mediana",
        score=1.0,
        window=None,
        created_at=NOW,
        expires_at=NOW + timedelta(hours=12),
        updated_at=NOW,
    )
    return replace(base, **changes)


def reel_cover(**changes: object) -> CoverAsset:
    """A fresh unused 1080x1920 reel cover."""
    base = CoverAsset(
        asset_id=uuid4(),
        creator_asset_id=uuid4(),
        kind=COVER_KIND_AI_IMAGE,
        source_url=None,
        width=1080,
        height=1920,
        created_at=NOW - timedelta(minutes=10),
        purpose=COVER_PURPOSE_REEL,
    )
    return replace(base, **changes)


@dataclass
class FakeReels:
    """``ReelGateway`` over a dict; ``fail`` raises on every call."""

    items: dict[str, ReelMedia] = field(default_factory=dict)
    collaborator_names: dict[str, tuple[str, ...]] = field(default_factory=dict)
    fail: InstagramCallError | None = None
    calls: list[str] = field(default_factory=list)

    async def list_reels(self, since: datetime) -> list[ReelMedia]:
        self.calls.append("list")
        self._raise()
        found = [r for r in self.items.values() if r.posted_at >= since]
        return sorted(found, key=lambda r: r.posted_at, reverse=True)

    async def reel(self, media_id: str) -> ReelMedia | None:
        self.calls.append(f"reel:{media_id}")
        self._raise()
        return self.items.get(media_id)

    async def collaborators(self, media_id: str) -> tuple[str, ...]:
        self.calls.append(f"collab:{media_id}")
        self._raise()
        return self.collaborator_names.get(media_id, ())

    def _raise(self) -> None:
        if self.fail is not None:
            raise self.fail


@dataclass
class FakeProbe:
    """``ReelProbe`` returning a fixed duration."""

    seconds: float | None = 60.0
    calls: int = 0

    async def duration(self, url: str) -> float | None:
        del url
        self.calls += 1
        return self.seconds


@dataclass
class FakeCovers:
    """``RepostCovers`` over a dict."""

    covers: dict[UUID, CoverAsset] = field(default_factory=dict)

    async def covers_by_ids(self, ids: tuple[UUID, ...]) -> dict[UUID, CoverAsset]:
        return {i: self.covers[i] for i in ids if i in self.covers}

    async def claim_for_repost(self, asset_id: UUID, repost_id: UUID) -> bool:
        cover = self.covers.get(asset_id)
        if cover is None or cover.is_used:
            return False
        self.covers[asset_id] = replace(cover, repost_id=repost_id)
        return True


@dataclass
class MemoryStore:
    """``RepostStore`` and ``ReelFactsStore`` in memory."""

    rows: dict[UUID, Repost] = field(default_factory=dict)
    fact_rows: dict[str, ReelFacts] = field(default_factory=dict)
    commits: int = 0
    locks: int = 0

    async def lock(self) -> None:
        self.locks += 1

    async def by_key(self, key: str) -> Repost | None:
        return next((r for r in self.rows.values() if r.idempotency_key == key), None)

    async def get(self, repost_id: UUID) -> Repost | None:
        return self.rows.get(repost_id)

    async def live_since(self, media_id: str, since: datetime) -> bool:
        return any(
            r.media_id == media_id
            and r.status in LIVE_STATUSES
            and r.created_at >= since
            for r in self.rows.values()
        )

    async def drafts_since(self, since: datetime) -> int:
        return sum(
            1
            for r in self.rows.values()
            if r.created_at >= since and r.status in CAP_STATUSES
        )

    async def insert(self, repost: Repost) -> None:
        self.rows[repost.id] = repost

    async def save(self, change: StatusChange) -> bool:
        current = self.rows.get(change.repost.id)
        if current is None or current.status != change.expected:
            return False
        self.rows[change.repost.id] = change.repost
        return True

    async def list_reposts(self, query: RepostListQuery) -> list[Repost]:
        rows = sorted(self.rows.values(), key=lambda r: r.created_at, reverse=True)
        if query.statuses:
            rows = [r for r in rows if r.status in query.statuses]
        if query.since is not None:
            rows = [r for r in rows if r.created_at >= query.since]
        return rows[: query.limit]

    async def due(self, now: datetime) -> list[Repost]:
        return [r for r in self.rows.values() if _due(r, now)]

    async def caption_editing(self, since: datetime) -> Repost | None:
        waiting = [
            r
            for r in self.rows.values()
            if r.status == STATUS_PENDING
            and r.caption_edit_at is not None
            and r.caption_edit_at >= since
        ]
        return waiting[0] if waiting else None

    async def latest_for(self, media_ids: Sequence[str]) -> dict[str, LastRepost]:
        found: dict[str, LastRepost] = {}
        for r in sorted(self.rows.values(), key=lambda r: r.created_at):
            if r.media_id in media_ids:
                found[r.media_id] = LastRepost(
                    repost_id=r.id,
                    status=r.status,
                    created_at=r.created_at,
                    published_at=r.published_at,
                )
        return found

    async def hidden_media(self, since: datetime | None) -> frozenset[str]:
        live = {
            r.media_id
            for r in self.rows.values()
            if since is not None and r.status in LIVE_STATUSES and r.created_at >= since
        }
        new = {r.new_media_id for r in self.rows.values() if r.new_media_id}
        return frozenset(live | new)

    async def facts(self, media_ids: Sequence[str]) -> dict[str, ReelFacts]:
        return {m: self.fact_rows[m] for m in media_ids if m in self.fact_rows}

    async def save_facts(self, facts: ReelFacts) -> None:
        self.fact_rows[facts.media_id] = facts

    async def commit(self) -> None:
        self.commits += 1


def _due(r: Repost, now: datetime) -> bool:
    if r.status == STATUS_PENDING:
        return r.preview_ready_at is None or r.expires_at <= now
    if r.status == STATUS_APPROVED:
        return r.publish_at is not None and r.publish_at <= now
    return r.status == STATUS_PROCESSING
