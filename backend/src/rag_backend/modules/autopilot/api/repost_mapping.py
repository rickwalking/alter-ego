"""Map bodies, errors and domain values for the Reels and repost routes."""

from __future__ import annotations

from fastapi.responses import JSONResponse
from pydantic import ValidationError

from rag_backend.modules.autopilot.api.repost_schemas import (
    LastRepostView,
    ReelMetricsView,
    ReelRatesView,
    ReelsBaselineView,
    ReelsView,
    ReelView,
    RepostAccepted,
    RepostCreate,
    RepostView,
)
from rag_backend.modules.autopilot.application.reels_service import ReelsPage
from rag_backend.modules.autopilot.domain.reels import ReelItem, cdn_expiry
from rag_backend.modules.autopilot.domain.repost import (
    PublishWindow,
    Repost,
    RepostDraft,
    RepostError,
    invalid,
)
from rag_backend.modules.autopilot.repost_constants import (
    FIELD_BODY,
    FILE_PREVIEW,
    PUBLIC_URL_TEMPLATE,
    STATUS_EXPIRED,
    STATUS_REJECTED,
)

_NO_PREVIEW = frozenset({STATUS_REJECTED, STATUS_EXPIRED})


def error_response(error: RepostError) -> JSONResponse:
    """``{"error": {"code", "message", "field"}}`` with the problem's status."""
    problem = error.problem
    return JSONResponse(
        status_code=problem.status,
        content={
            "error": {
                "code": problem.code,
                "message": error.message,
                "field": problem.field,
            }
        },
    )


def invalid_body(exc: ValidationError) -> RepostError:
    """The first Pydantic error as a 400 ``invalid_field``."""
    errors = exc.errors()
    if not errors:
        return invalid(FIELD_BODY, "invalid JSON body")
    first = errors[0]
    field = ".".join(str(part) for part in first["loc"]) or FIELD_BODY
    return invalid(field, str(first["msg"]))


def draft_from(body: RepostCreate, key: str) -> RepostDraft:
    """The domain draft of a parsed body."""
    window = body.publish_window
    return RepostDraft(
        media_id=body.media_id.strip(),
        caption=body.caption,
        hook_text=body.hook_text,
        hook_duration_s=body.hook_duration_s,
        trim_start_s=body.trim_start_s,
        trim_end_s=body.trim_end_s,
        cover_asset_id=None if body.cover is None else body.cover.asset_id,
        collaborators=None if body.collaborators is None else tuple(body.collaborators),
        share_to_feed=body.share_to_feed,
        reason=body.reason,
        score=body.score,
        window=None
        if window is None
        else PublishWindow(earliest=window.earliest, latest=window.latest),
        idempotency_key=key,
        override_weekly_cap=body.override_weekly_cap,
        source_asset_id=body.source_asset_id,
    )


def preview_url(base: str, repost: Repost) -> str:
    """The keyless preview URL of a draft."""
    return PUBLIC_URL_TEMPLATE.format(
        base=base.rstrip("/"), repost_id=repost.id, file_name=FILE_PREVIEW
    )


def accepted(repost: Repost, base: str) -> RepostAccepted:
    """The 202 body."""
    return RepostAccepted(
        id=repost.id,
        status=repost.status,
        media_id=repost.media_id,
        permalink=repost.permalink,
        preview_url=preview_url(base, repost),
        expires_at=repost.expires_at,
        created_at=repost.created_at,
    )


def repost_view(repost: Repost, base: str) -> RepostView:
    """A draft's status; ``cover_used`` once the owner approved."""
    previewable = (
        repost.preview_ready_at is not None and repost.status not in _NO_PREVIEW
    )
    return RepostView(
        id=repost.id,
        status=repost.status,
        media_id=repost.media_id,
        permalink=repost.permalink,
        new_media_id=repost.new_media_id,
        new_permalink=repost.new_permalink,
        cover_used=repost.cover_choice,
        publish_at=repost.publish_at,
        preview_url=preview_url(base, repost) if previewable else None,
        error_code=repost.error_code,
        error_message=repost.error_message,
        created_at=repost.created_at,
        expires_at=repost.expires_at,
        approved_at=repost.approved_at,
        published_at=repost.published_at,
    )


def reels_view(page: ReelsPage) -> ReelsView:
    """The ``GET /reels`` body."""
    return ReelsView(
        items=[reel_view(item) for item in page.items],
        baseline=ReelsBaselineView(
            median_views=page.baseline.median_views,
            median_shares_per_100_views=page.baseline.median_shares_per_100_views,
            median_engagement_rate=page.baseline.median_engagement_rate,
        ),
        next_cursor=page.next_cursor,
        generated_at=page.generated_at,
    )


def reel_view(item: ReelItem) -> ReelView:
    """One Reel row."""
    media, facts = item.media, item.facts
    return ReelView(
        media_id=media.media_id,
        shortcode=media.shortcode,
        permalink=media.permalink,
        media_product_type=media.product_type,
        timestamp=media.posted_at,
        age_days=item.age_days,
        caption=media.caption,
        collaborators=[] if facts is None else list(facts.collaborators),
        duration_s=None if facts is None else facts.duration_s,
        thumbnail_url=media.thumbnail_url,
        video_url=media.video_url,
        video_url_expires_at=cdn_expiry(media.video_url),
        metrics=_metrics(item),
        rates=_rates(item),
        stale=item.stale,
        last_repost=_last(item),
    )


def _metrics(item: ReelItem) -> ReelMetricsView:
    m = item.metrics
    return ReelMetricsView(
        views=m.views,
        reach=m.reach,
        likes=m.likes,
        comments=m.comments,
        saved=m.saved,
        shares=m.shares,
        follows=m.follows,
        avg_watch_time_ms=m.avg_watch_time_ms,
        total_watch_time_ms=m.total_watch_time_ms,
    )


def _rates(item: ReelItem) -> ReelRatesView:
    base = item.rates.base
    return ReelRatesView(
        shares_per_100_views=base.shares_per_100_views,
        saves_per_100_reach=base.saves_per_100_reach,
        follows_per_1000_reach=base.follows_per_1000_reach,
        engagement_rate=base.engagement_rate,
        avg_watch_ratio=item.rates.avg_watch_ratio,
    )


def _last(item: ReelItem) -> LastRepostView | None:
    last = item.last_repost
    if last is None:
        return None
    return LastRepostView(
        repost_id=last.repost_id,
        status=last.status,
        created_at=last.created_at,
        published_at=last.published_at,
    )


__all__ = [
    "accepted",
    "draft_from",
    "error_response",
    "invalid_body",
    "preview_url",
    "reel_view",
    "reels_view",
    "repost_view",
]
