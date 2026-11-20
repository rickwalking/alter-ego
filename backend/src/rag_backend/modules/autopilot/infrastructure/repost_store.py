"""SQL store of repost drafts and the Reel facts cache (ADR-0031).

``save`` is a compare-and-set on the status, so a webhook tap and a worker
tick never both move the same draft. The caller commits.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.reels import LastRepost, ReelFacts
from rag_backend.modules.autopilot.domain.repost import (
    PublishWindow,
    Repost,
    RepostListQuery,
)
from rag_backend.modules.autopilot.domain.repost_ports import StatusChange
from rag_backend.modules.autopilot.infrastructure.advisory_lock import (
    advisory_xact_lock,
)
from rag_backend.modules.autopilot.infrastructure.repost_models import (
    ReelFactsModel,
    RepostModel,
)
from rag_backend.modules.autopilot.infrastructure.run_mapping import aware
from rag_backend.modules.autopilot.repost_constants import (
    ADVISORY_LOCK_REPOST,
    CAP_STATUSES,
    LIVE_STATUSES,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_PROCESSING,
    TICK_SCAN,
)

_R = RepostModel


class SqlRepostStore:
    """``RepostStore`` and ``ReelFactsStore`` on one session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock(self) -> None:
        """Hold the repost advisory lock until commit or rollback."""
        await advisory_xact_lock(self._session, ADVISORY_LOCK_REPOST)

    async def by_key(self, key: str) -> Repost | None:
        """The draft for an idempotency key."""
        row = await self._session.scalar(select(_R).where(_R.idempotency_key == key))
        return None if row is None else to_repost(row)

    async def get(self, repost_id: UUID) -> Repost | None:
        """One draft."""
        row = await self._session.get(_R, repost_id)
        return None if row is None else to_repost(row)

    async def live_since(self, media_id: str, since: datetime) -> bool:
        """A live repost of the Reel created since ``since``."""
        found = await self._session.scalar(
            select(_R.id)
            .where(
                _R.media_id == media_id,
                _R.status.in_(LIVE_STATUSES),
                _R.created_at >= since,
            )
            .limit(1)
        )
        return found is not None

    async def drafts_since(self, since: datetime) -> int:
        """Drafts that count toward the weekly cap (failed ones do not)."""
        count = await self._session.scalar(
            select(func.count())
            .select_from(_R)
            .where(_R.created_at >= since, _R.status.in_(CAP_STATUSES))
        )
        return int(count or 0)

    async def insert(self, repost: Repost) -> None:
        """Add the draft."""
        row = RepostModel(id=repost.id)
        _fill(row, repost)
        self._session.add(row)
        await self._session.flush()

    async def save(self, change: StatusChange) -> bool:
        """Replace the row while its status is still ``expected``."""
        values = _values(change.repost)
        result = await self._session.execute(
            update(_R)
            .where(_R.id == change.repost.id, _R.status == change.expected)
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        self._session.expire_all()
        return cast(CursorResult[object], result).rowcount == 1

    async def list_reposts(self, query: RepostListQuery) -> list[Repost]:
        """Newest first, filtered by status and creation time."""
        stmt = select(_R).order_by(_R.created_at.desc()).limit(query.limit)
        if query.statuses:
            stmt = stmt.where(_R.status.in_(query.statuses))
        if query.since is not None:
            stmt = stmt.where(_R.created_at >= query.since)
        rows = await self._session.scalars(stmt)
        return [to_repost(row) for row in rows]

    async def due(self, now: datetime) -> list[Repost]:
        """To render, expire, publish or poll; oldest first."""
        pending = _R.status == STATUS_PENDING
        rows = await self._session.scalars(
            select(_R)
            .where(
                or_(
                    and_(pending, _R.preview_ready_at.is_(None)),
                    and_(pending, _R.expires_at <= now),
                    and_(_R.status == STATUS_APPROVED, _R.publish_at <= now),
                    _R.status == STATUS_PROCESSING,
                )
            )
            .order_by(_R.created_at)
            .limit(TICK_SCAN)
        )
        return [to_repost(row) for row in rows]

    async def caption_editing(self, since: datetime) -> Repost | None:
        """The pending draft whose caption edit was asked for since ``since``."""
        row = await self._session.scalar(
            select(_R)
            .where(_R.status == STATUS_PENDING, _R.caption_edit_at >= since)
            .order_by(_R.caption_edit_at.desc())
            .limit(1)
        )
        return None if row is None else to_repost(row)

    async def latest_for(self, media_ids: Sequence[str]) -> dict[str, LastRepost]:
        """The newest repost per original Reel."""
        if not media_ids:
            return {}
        rows = await self._session.scalars(
            select(_R).where(_R.media_id.in_(list(media_ids))).order_by(_R.created_at)
        )
        return {row.media_id: _last(row) for row in rows}

    async def hidden_media(self, since: datetime | None) -> frozenset[str]:
        """Every repost's new media, plus Reels with a live repost since ``since``."""
        reposted = await self._session.scalars(
            select(_R.new_media_id).where(_R.new_media_id.is_not(None))
        )
        hidden = frozenset(m for m in reposted.all() if m)
        if since is None:
            return hidden
        live = await self._session.scalars(
            select(_R.media_id).where(
                _R.status.in_(LIVE_STATUSES), _R.created_at >= since
            )
        )
        return hidden | frozenset(live.all())

    async def facts(self, media_ids: Sequence[str]) -> dict[str, ReelFacts]:
        """Cached facts per media id."""
        if not media_ids:
            return {}
        rows = await self._session.scalars(
            select(ReelFactsModel).where(ReelFactsModel.media_id.in_(list(media_ids)))
        )
        return {row.media_id: _facts(row) for row in rows}

    async def save_facts(self, facts: ReelFacts) -> None:
        """Insert or replace one facts row."""
        row = await self._session.get(ReelFactsModel, facts.media_id)
        if row is None:
            row = ReelFactsModel(media_id=facts.media_id)
            self._session.add(row)
        row.duration_s = facts.duration_s
        row.collaborators = list(facts.collaborators)
        row.probed_at = facts.probed_at
        await self._session.flush()

    async def commit(self) -> None:
        """Commit the session."""
        await self._session.commit()


def _values(repost: Repost) -> dict[str, object]:
    window = repost.window
    return {
        "idempotency_key": repost.idempotency_key,
        "request_hash": repost.request_hash,
        "media_id": repost.media_id,
        "status": repost.status,
        "permalink": repost.permalink,
        "caption": repost.caption,
        "hook_text": repost.hook_text,
        "hook_duration_s": repost.hook_duration_s,
        "trim_start_s": repost.trim_start_s,
        "trim_end_s": repost.trim_end_s,
        "cover_asset_id": repost.cover_asset_id,
        "collaborators": list(repost.collaborators),
        "share_to_feed": repost.share_to_feed,
        "reason": repost.reason,
        "score": repost.score,
        "publish_earliest": None if window is None else window.earliest,
        "publish_latest": None if window is None else window.latest,
        "created_at": repost.created_at,
        "expires_at": repost.expires_at,
        "updated_at": repost.updated_at or repost.created_at,
        "cover_choice": repost.cover_choice,
        "publish_at": repost.publish_at,
        "approved_at": repost.approved_at,
        "decided_by": repost.decided_by,
        "preview_ready_at": repost.preview_ready_at,
        "telegram_message_id": repost.telegram_message_id,
        "caption_edit_at": repost.caption_edit_at,
        "container_id": repost.container_id,
        "container_created_at": repost.container_created_at,
        "new_media_id": repost.new_media_id,
        "new_permalink": repost.new_permalink,
        "error_code": repost.error_code,
        "error_message": repost.error_message,
        "published_at": repost.published_at,
    }


def _fill(row: RepostModel, repost: Repost) -> None:
    for name, value in _values(repost).items():
        setattr(row, name, value)


def to_repost(row: RepostModel) -> Repost:
    """The domain value of a row (timestamps made UTC-aware)."""
    return Repost(
        id=row.id,
        idempotency_key=row.idempotency_key,
        request_hash=row.request_hash,
        media_id=row.media_id,
        status=row.status,
        permalink=row.permalink,
        caption=row.caption,
        hook_text=row.hook_text,
        hook_duration_s=row.hook_duration_s,
        trim_start_s=row.trim_start_s,
        trim_end_s=row.trim_end_s,
        cover_asset_id=row.cover_asset_id,
        collaborators=tuple(row.collaborators or ()),
        share_to_feed=row.share_to_feed,
        reason=row.reason,
        score=row.score,
        window=_window(row),
        created_at=_at(row.created_at),
        expires_at=_at(row.expires_at),
        updated_at=aware(row.updated_at),
        cover_choice=row.cover_choice,
        publish_at=aware(row.publish_at),
        approved_at=aware(row.approved_at),
        decided_by=row.decided_by,
        preview_ready_at=aware(row.preview_ready_at),
        telegram_message_id=row.telegram_message_id,
        caption_edit_at=aware(row.caption_edit_at),
        container_id=row.container_id,
        container_created_at=aware(row.container_created_at),
        new_media_id=row.new_media_id,
        new_permalink=row.new_permalink,
        error_code=row.error_code,
        error_message=row.error_message,
        published_at=aware(row.published_at),
    )


def _window(row: RepostModel) -> PublishWindow | None:
    earliest = aware(row.publish_earliest)
    latest = aware(row.publish_latest)
    if earliest is None or latest is None:
        return None
    return PublishWindow(earliest=earliest, latest=latest)


def _at(value: datetime) -> datetime:
    made = aware(value)
    return made if made is not None else value


def _last(row: RepostModel) -> LastRepost:
    return LastRepost(
        repost_id=row.id,
        status=row.status,
        created_at=_at(row.created_at),
        published_at=aware(row.published_at),
    )


def _facts(row: ReelFactsModel) -> ReelFacts:
    return ReelFacts(
        media_id=row.media_id,
        duration_s=row.duration_s,
        collaborators=tuple(row.collaborators or ()),
        probed_at=_at(row.probed_at),
    )


__all__ = ["SqlRepostStore", "to_repost"]
