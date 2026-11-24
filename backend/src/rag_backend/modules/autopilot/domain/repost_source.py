"""An owner-supplied source video for a repost draft, and its checks.

The scout uploads the original high-quality take; the draft then renders from
it instead of the Instagram CDN copy. Only the pure rules live here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from rag_backend.modules.autopilot.repost_source_constants import (
    ERR_SOURCE_CODEC,
    ERR_SOURCE_DURATION,
    ERR_SOURCE_NOT_VIDEO,
    ERR_SOURCE_SHAPE,
    SOURCE_CODEC_H264,
    SOURCE_MAX_SECONDS,
    SOURCE_MIN_SECONDS,
    SOURCE_MIN_WIDTH,
    SOURCE_TTL_HOURS,
)


class SourceError(Exception):
    """An upload was refused; ``code`` is the API error code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, kw_only=True)
class VideoProbe:
    """What ffprobe read from the first video stream."""

    codec: str
    width: int
    height: int
    duration_s: float


@dataclass(frozen=True, kw_only=True)
class RepostSource:
    """One stored source video and the draft that used it, if any."""

    id: UUID
    file_name: str
    size_bytes: int
    probe: VideoProbe
    created_at: datetime
    repost_id: UUID | None = None


def check_video(probe: VideoProbe | None) -> VideoProbe:
    """An H.264 portrait video of 3-180 s, else ``SourceError``."""
    if probe is None:
        raise SourceError(ERR_SOURCE_NOT_VIDEO)
    if probe.codec != SOURCE_CODEC_H264:
        raise SourceError(ERR_SOURCE_CODEC)
    if probe.width < SOURCE_MIN_WIDTH or probe.height <= probe.width:
        raise SourceError(ERR_SOURCE_SHAPE)
    if not SOURCE_MIN_SECONDS <= probe.duration_s <= SOURCE_MAX_SECONDS:
        raise SourceError(ERR_SOURCE_DURATION)
    return probe


def source_expired(source: RepostSource, now: datetime) -> bool:
    """True once the upload is older than its time to live."""
    return now - source.created_at >= timedelta(hours=SOURCE_TTL_HOURS)


def source_usable(source: RepostSource | None, now: datetime) -> bool:
    """A fresh upload no draft has used yet."""
    if source is None or source.repost_id is not None:
        return False
    return not source_expired(source, now)


__all__ = [
    "RepostSource",
    "SourceError",
    "VideoProbe",
    "check_video",
    "source_expired",
    "source_usable",
]
