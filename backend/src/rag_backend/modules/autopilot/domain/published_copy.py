"""The owner's "published" notice: post link, Story outcome, music nudge (AE-0369).

Pure. The publish job writes the Story outcome and the music style on the
outbox payload; this module reads them back and builds the Telegram text.
An event without them (written before AE-0369, or by a publisher that cannot
post Stories) gets only the post line.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from rag_backend.modules.autopilot.domain.publish import PostExtras
from rag_backend.modules.autopilot.schedule_constants import (
    PAYLOAD_LATE_MINUTES,
    TEXT_LATE_SUFFIX,
)
from rag_backend.modules.autopilot.story_constants import (
    NOTICE_LINE_SEPARATOR,
    PAYLOAD_MUSIC_STYLE,
    PAYLOAD_STORY_ERROR,
    PAYLOAD_STORY_STATUS,
    STORY_OUTCOME_FAILED,
    STORY_OUTCOME_PUBLISHED,
    TEXT_MUSIC_NUDGE,
    TEXT_PUBLISHED_PT,
    TEXT_PUBLISHED_PT_NO_LINK,
    TEXT_STORY_FAILED,
    TEXT_STORY_PUBLISHED,
)


def extras_payload(extras: PostExtras | None) -> dict[str, object]:
    """The outbox payload keys for the extras. Empty without extras."""
    if extras is None:
        return {}
    return {
        PAYLOAD_STORY_STATUS: extras.story_status,
        PAYLOAD_STORY_ERROR: extras.story_error,
        PAYLOAD_MUSIC_STYLE: extras.music_style,
        PAYLOAD_LATE_MINUTES: extras.late_minutes,
    }


def with_late(extras: PostExtras | None, late: int | None) -> PostExtras | None:
    """Add the scheduled run's delay (AE-0370). Without a Story, only the delay."""
    if late is None:
        return extras
    if extras is None:
        return PostExtras(
            story_status="", story_error=None, music_style="", late_minutes=late
        )
    return replace(extras, late_minutes=late)


def post_extras_of(payload: Mapping[str, object]) -> PostExtras | None:
    """The extras an outbox payload carries, or None when it has none."""
    status = payload.get(PAYLOAD_STORY_STATUS)
    music = payload.get(PAYLOAD_MUSIC_STYLE)
    if not isinstance(status, str) or not isinstance(music, str):
        return None
    error = payload.get(PAYLOAD_STORY_ERROR)
    late = payload.get(PAYLOAD_LATE_MINUTES)
    return PostExtras(
        story_status=status,
        story_error=error if isinstance(error, str) else None,
        music_style=music,
        late_minutes=_minutes(late),
    )


def published_text(permalink: str, extras: PostExtras | None) -> str:
    """The post line, then the Story line and the music nudge when known."""
    lines = [_headline(permalink) + _late_suffix(extras)]
    if extras is not None:
        lines.extend(_extra_lines(extras))
    return NOTICE_LINE_SEPARATOR.join(lines)


def _late_suffix(extras: PostExtras | None) -> str:
    if extras is None or extras.late_minutes is None:
        return ""
    return TEXT_LATE_SUFFIX.format(minutes=extras.late_minutes)


def _minutes(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _headline(permalink: str) -> str:
    if not permalink:
        return TEXT_PUBLISHED_PT_NO_LINK
    return TEXT_PUBLISHED_PT.format(permalink=permalink)


def _extra_lines(extras: PostExtras) -> list[str]:
    lines: list[str] = []
    story = _story_line(extras)
    if story:
        lines.append(story)
    if extras.music_style:
        lines.append(TEXT_MUSIC_NUDGE.format(style=extras.music_style))
    return lines


def _story_line(extras: PostExtras) -> str:
    if extras.story_status == STORY_OUTCOME_PUBLISHED:
        return TEXT_STORY_PUBLISHED
    if extras.story_status == STORY_OUTCOME_FAILED:
        return TEXT_STORY_FAILED.format(reason=extras.story_error or "")
    return ""
