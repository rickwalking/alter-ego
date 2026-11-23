"""Create and read repost drafts. The API key can never approve one (ADR-0031).

A new draft is ``pending_approval`` with no preview. The worker renders the
preview and only then messages the owner, so ``POST /repost`` never waits
for a video.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import structlog

from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.reels import ReelFacts, ReelMedia
from rag_backend.modules.autopilot.domain.repost import (
    Repost,
    RepostDraft,
    RepostError,
    RepostListQuery,
    RepostProblem,
    request_hash,
)
from rag_backend.modules.autopilot.domain.repost_ports import (
    ReelFactsStore,
    ReelGateway,
    ReelProbe,
    RepostCovers,
    RepostStore,
)
from rag_backend.modules.autopilot.domain.repost_rules import (
    EligibilityFacts,
    check_eligibility,
    check_fields,
    recent_since,
)
from rag_backend.modules.autopilot.domain.topic_text import strip_controls
from rag_backend.modules.autopilot.repost_constants import (
    APPROVAL_TTL_HOURS,
    ERR_ASSET_INVALID,
    ERR_IDEMPOTENCY_CONFLICT,
    ERR_NOT_CONFIGURED,
    ERR_REPOST_NOT_FOUND,
    ERR_UNAVAILABLE,
    HTTP_CONFLICT,
    HTTP_NOT_FOUND,
    HTTP_UNAVAILABLE,
    HTTP_UNPROCESSABLE,
    LOG_CREATED,
    LOG_REPOST,
    REPOST_WINDOW_DAYS,
    STATUS_PENDING,
    WEEK_DAYS,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class RepostDeps:
    """Stores, Graph, the duration probe and the clock."""

    store: RepostStore
    covers: RepostCovers
    facts: ReelFactsStore
    reels: ReelGateway | None
    probe: ReelProbe | None
    clock: Clock


@dataclass(frozen=True, kw_only=True)
class _Known:
    reel: ReelMedia | None
    facts: ReelFacts | None


class RepostDraftService:
    """``POST /repost``, ``GET /repost/{id}`` and ``GET /reposts``."""

    def __init__(self, deps: RepostDeps) -> None:
        self._deps = deps

    async def create(self, draft: RepostDraft) -> Repost:
        """Store a pending draft, or replay its idempotency key."""
        draft = cleaned(draft)
        now = self._deps.clock.now()
        check_fields(draft, now)
        replayed = await self._replay(draft)
        if replayed is not None:
            return replayed
        await self._deps.store.lock()
        replayed = await self._replay(draft)
        if replayed is not None:
            return replayed
        known = await self._known(draft.media_id, now)
        await self._check(draft, known, now)
        repost = _pending(draft, known, now)
        await self._store(repost)
        logger.info(
            LOG_REPOST,
            outcome=LOG_CREATED,
            repost_id=str(repost.id),
            cap_override=draft.override_weekly_cap,
        )
        return repost

    async def get(self, repost_id: UUID) -> Repost:
        """The draft, or 404 ``repost_not_found``."""
        found = await self._deps.store.get(repost_id)
        if found is None:
            raise RepostError(
                RepostProblem(code=ERR_REPOST_NOT_FOUND, status=HTTP_NOT_FOUND)
            )
        return found

    async def list(self, query: RepostListQuery) -> list[Repost]:
        """Newest first."""
        return await self._deps.store.list_reposts(query)

    async def _replay(self, draft: RepostDraft) -> Repost | None:
        existing = await self._deps.store.by_key(draft.idempotency_key)
        if existing is None:
            return None
        if existing.request_hash != request_hash(draft):
            raise RepostError(
                RepostProblem(code=ERR_IDEMPOTENCY_CONFLICT, status=HTTP_CONFLICT)
            )
        return existing

    async def _known(self, media_id: str, now: datetime) -> _Known:
        reels = self._deps.reels
        if reels is None:
            raise _unavailable(ERR_NOT_CONFIGURED)
        try:
            reel = await reels.reel(media_id)
        except InstagramCallError:
            raise _unavailable(ERR_UNAVAILABLE) from None
        if reel is None:
            return _Known(reel=None, facts=None)
        return _Known(reel=reel, facts=await self._facts(reel, now))

    async def _facts(self, reel: ReelMedia, now: datetime) -> ReelFacts:
        cached = (await self._deps.facts.facts([reel.media_id])).get(reel.media_id)
        if cached is not None and cached.duration_s is not None:
            return cached
        duration = None
        if self._deps.probe is not None and reel.video_url:
            duration = await self._deps.probe.duration(reel.video_url)
        collaborators = await _collaborators(self._deps.reels, reel.media_id)
        facts = ReelFacts(
            media_id=reel.media_id,
            duration_s=duration,
            collaborators=collaborators,
            probed_at=now,
        )
        await self._deps.facts.save_facts(facts)
        return facts

    async def _check(self, draft: RepostDraft, known: _Known, now: datetime) -> None:
        store = self._deps.store
        cover = None
        if draft.cover_asset_id is not None:
            found = await self._deps.covers.covers_by_ids((draft.cover_asset_id,))
            cover = found.get(draft.cover_asset_id)
        facts = EligibilityFacts(
            now=now,
            reel=known.reel,
            duration_s=None if known.facts is None else known.facts.duration_s,
            live_repost=await store.live_since(
                draft.media_id, recent_since(now, REPOST_WINDOW_DAYS)
            ),
            recent_drafts=await store.drafts_since(recent_since(now, WEEK_DAYS)),
            cover=cover,
        )
        check_eligibility(draft, facts)

    async def _store(self, repost: Repost) -> None:
        await self._deps.store.insert(repost)
        asset = repost.cover_asset_id
        if asset is not None and not await self._deps.covers.claim_for_repost(
            asset, repost.id
        ):
            raise RepostError(
                RepostProblem(code=ERR_ASSET_INVALID, status=HTTP_UNPROCESSABLE)
            )
        await self._deps.store.commit()


def cleaned(draft: RepostDraft) -> RepostDraft:
    """Control characters stripped; a blank hook is no hook."""
    hook = strip_controls(draft.hook_text or "").strip() or None
    return replace(
        draft,
        caption=strip_controls(draft.caption).strip(),
        reason=strip_controls(draft.reason).strip(),
        hook_text=hook,
    )


async def _collaborators(reels: ReelGateway | None, media_id: str) -> tuple[str, ...]:
    if reels is None:
        return ()
    try:
        return await reels.collaborators(media_id)
    except InstagramCallError:
        return ()


def _pending(draft: RepostDraft, known: _Known, now: datetime) -> Repost:
    collaborators = draft.collaborators
    if collaborators is None:
        collaborators = () if known.facts is None else known.facts.collaborators
    return Repost(
        id=uuid4(),
        idempotency_key=draft.idempotency_key,
        request_hash=request_hash(draft),
        media_id=draft.media_id,
        status=STATUS_PENDING,
        permalink=None if known.reel is None else known.reel.permalink,
        caption=draft.caption,
        hook_text=draft.hook_text,
        hook_duration_s=draft.hook_duration_s,
        trim_start_s=draft.trim_start_s,
        trim_end_s=draft.trim_end_s,
        cover_asset_id=draft.cover_asset_id,
        collaborators=collaborators,
        share_to_feed=draft.share_to_feed,
        reason=draft.reason,
        score=draft.score,
        window=draft.window,
        created_at=now,
        expires_at=now + timedelta(hours=APPROVAL_TTL_HOURS),
        updated_at=now,
    )


def _unavailable(code: str) -> RepostError:
    return RepostError(RepostProblem(code=code, status=HTTP_UNAVAILABLE))


__all__ = ["RepostDeps", "RepostDraftService", "cleaned"]
