"""Repost draft rules: field checks (400) and eligibility (404/409/422). Pure."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from rag_backend.domain.constants.slide_cover import (
    COVER_KIND_AI_IMAGE,
    COVER_PURPOSE_REEL,
    REEL_COVER_HEIGHT,
    REEL_COVER_WIDTH,
)
from rag_backend.modules.autopilot.domain.cover import CoverAsset, is_expired
from rag_backend.modules.autopilot.domain.reels import ReelMedia, age_days
from rag_backend.modules.autopilot.domain.repost import (
    RepostDraft,
    RepostError,
    RepostProblem,
    invalid,
)
from rag_backend.modules.autopilot.ig_media_constants import PRODUCT_REELS
from rag_backend.modules.autopilot.repost_constants import (
    CAPTION_MAX,
    COLLABORATORS_MAX,
    ERR_ALREADY_REPOSTED,
    ERR_ASSET_INVALID,
    ERR_REEL_NOT_FOUND,
    ERR_SOURCE_UNAVAILABLE,
    ERR_TOO_RECENT,
    ERR_WEEKLY_CAP,
    FIELD_CAPTION,
    FIELD_COLLABORATORS,
    FIELD_HOOK_DURATION,
    FIELD_HOOK_TEXT,
    FIELD_MEDIA_ID,
    FIELD_REASON,
    FIELD_TRIM_END,
    FIELD_TRIM_START,
    FIELD_WINDOW_EARLIEST,
    FIELD_WINDOW_LATEST,
    FINAL_MAX_SECONDS,
    FINAL_MIN_SECONDS,
    HASHTAG_PATTERN,
    HASHTAGS_MAX,
    HOOK_DURATION_MAX,
    HOOK_TEXT_MAX,
    HTTP_CONFLICT,
    HTTP_NOT_FOUND,
    HTTP_UNPROCESSABLE,
    MEDIA_ID_MAX,
    MENTION_PATTERN,
    MENTIONS_MAX,
    MIN_AGE_DAYS,
    REASON_MAX,
    REASON_MIN,
    USERNAME_PATTERN,
    WEEKLY_CAP,
)

_HASHTAG = re.compile(HASHTAG_PATTERN)
_MENTION = re.compile(MENTION_PATTERN)
_USERNAME = re.compile(USERNAME_PATTERN)


@dataclass(frozen=True, kw_only=True)
class EligibilityFacts:
    """What the stores and Graph know about the draft's Reel and cover."""

    now: datetime
    reel: ReelMedia | None
    duration_s: float | None
    live_repost: bool
    recent_drafts: int
    cover: CoverAsset | None


def check_fields(draft: RepostDraft, now: datetime) -> None:
    """Every field rule of the spec; raises 400 ``invalid_field``."""
    if not draft.media_id.isdigit() or len(draft.media_id) > MEDIA_ID_MAX:
        raise invalid(FIELD_MEDIA_ID, "digits only")
    check_caption(draft.caption)
    _check_hook(draft)
    _check_trim(draft)
    _check_reason(draft.reason)
    _check_collaborators(draft.collaborators)
    _check_window(draft, now)


def check_caption(caption: str) -> None:
    """1-2200 characters, at most 30 hashtags and 20 @mentions."""
    if not caption.strip() or len(caption) > CAPTION_MAX:
        raise invalid(FIELD_CAPTION, "1-2200 characters")
    if len(_HASHTAG.findall(caption)) > HASHTAGS_MAX:
        raise invalid(FIELD_CAPTION, "at most 30 hashtags")
    if len(_MENTION.findall(caption)) > MENTIONS_MAX:
        raise invalid(FIELD_CAPTION, "at most 20 @mentions")


def check_eligibility(draft: RepostDraft, facts: EligibilityFacts) -> None:
    """404 / 422 / 409 refusals, in the order the spec lists them."""
    reel = facts.reel
    if reel is None or reel.product_type != PRODUCT_REELS:
        raise _refuse(ERR_REEL_NOT_FOUND, HTTP_NOT_FOUND)
    if age_days(reel.posted_at, facts.now) < MIN_AGE_DAYS:
        raise _refuse(ERR_TOO_RECENT, HTTP_UNPROCESSABLE)
    if not reel.video_url:
        raise _refuse(ERR_SOURCE_UNAVAILABLE, HTTP_UNPROCESSABLE)
    if facts.live_repost:
        raise _refuse(ERR_ALREADY_REPOSTED, HTTP_CONFLICT)
    if facts.recent_drafts >= WEEKLY_CAP and not draft.override_weekly_cap:
        raise _refuse(ERR_WEEKLY_CAP, HTTP_UNPROCESSABLE)
    if draft.cover_asset_id is not None and not cover_usable(facts.cover, facts.now):
        raise _refuse(ERR_ASSET_INVALID, HTTP_UNPROCESSABLE)
    check_final_length(draft, facts.duration_s)


def cover_usable(cover: CoverAsset | None, now: datetime) -> bool:
    """A fresh, unused 1080x1920 ``ai_image`` uploaded as a reel cover."""
    if cover is None or cover.is_used or is_expired(cover, now):
        return False
    if cover.purpose != COVER_PURPOSE_REEL or cover.kind != COVER_KIND_AI_IMAGE:
        return False
    return (cover.width, cover.height) == (REEL_COVER_WIDTH, REEL_COVER_HEIGHT)


def check_final_length(draft: RepostDraft, duration_s: float | None) -> None:
    """The trimmed video must last 3-90 s. Unknown duration: only the trim pair."""
    end = draft.trim_end_s if draft.trim_end_s is not None else duration_s
    if end is None:
        return
    if duration_s is not None and draft.trim_start_s >= duration_s:
        raise invalid(FIELD_TRIM_START, "past the end of the video")
    if duration_s is not None:
        end = min(end, duration_s)
    if not FINAL_MIN_SECONDS <= end - draft.trim_start_s <= FINAL_MAX_SECONDS:
        raise invalid(FIELD_TRIM_END, "final video must be 3-90 s")


def recent_since(now: datetime, days: int) -> datetime:
    """The start of a rolling window of ``days`` days."""
    return now - timedelta(days=days)


def _check_hook(draft: RepostDraft) -> None:
    if draft.hook_text is not None and len(draft.hook_text) > HOOK_TEXT_MAX:
        raise invalid(FIELD_HOOK_TEXT, "at most 90 characters")
    duration = draft.hook_duration_s
    if not math.isfinite(duration) or not 0 < duration <= HOOK_DURATION_MAX:
        raise invalid(FIELD_HOOK_DURATION, "between 0 and 4 seconds")


def _check_trim(draft: RepostDraft) -> None:
    start = draft.trim_start_s
    if not math.isfinite(start) or start < 0:
        raise invalid(FIELD_TRIM_START, "0 or more seconds")
    end = draft.trim_end_s
    if end is None:
        return
    if not math.isfinite(end) or end <= start:
        raise invalid(FIELD_TRIM_END, "after trim_start_s")


def _check_reason(reason: str) -> None:
    if not REASON_MIN <= len(reason.strip()) <= REASON_MAX:
        raise invalid(FIELD_REASON, "10-600 characters")


def _check_collaborators(names: tuple[str, ...] | None) -> None:
    if names is None:
        return
    if len(names) > COLLABORATORS_MAX:
        raise invalid(FIELD_COLLABORATORS, "at most 3 usernames")
    if any(_USERNAME.fullmatch(name) is None for name in names):
        raise invalid(FIELD_COLLABORATORS, "Instagram usernames without @")


def _check_window(draft: RepostDraft, now: datetime) -> None:
    window = draft.window
    if window is None:
        return
    if window.earliest.tzinfo is None:
        raise invalid(FIELD_WINDOW_EARLIEST, "ISO 8601 with a timezone")
    if window.latest.tzinfo is None:
        raise invalid(FIELD_WINDOW_LATEST, "ISO 8601 with a timezone")
    if window.latest <= window.earliest or window.latest <= now:
        raise invalid(FIELD_WINDOW_LATEST, "after earliest and in the future")


def _refuse(code: str, status: int) -> RepostError:
    return RepostError(RepostProblem(code=code, status=status))


__all__ = [
    "EligibilityFacts",
    "check_caption",
    "check_eligibility",
    "check_fields",
    "check_final_length",
    "cover_usable",
    "recent_since",
]
