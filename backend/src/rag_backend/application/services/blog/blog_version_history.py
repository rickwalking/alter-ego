"""Version snapshots of a blog post (AE-0424, F-13).

Every content write (PUT, restore, image/rewrite/translation writes) appends one
entry to ``blog_posts.version_history`` in the same transaction as the write.
An entry snapshots the state **before** the write (title, excerpt, ``blog.v2``
content), so the first save keeps the original (e.g. AI-written) draft and any
earlier state can be restored. History is bounded: the first entry (the
original draft) is always kept plus the most recent ones, up to
``BLOG_VERSION_HISTORY_MAX``. A write whose pre-state equals the newest entry
adds nothing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from rag_backend.domain.constants.blog_editor import (
    BLOG_VERSION_HISTORY_MAX,
    VERSION_CONTENT_TYPE_BLOG_POST,
)

KEY_VERSION_NUMBER = "version_number"
KEY_SNAPSHOT = "snapshot"
KEY_TITLE = "title"
KEY_EXCERPT = "excerpt"


@dataclass(frozen=True)
class VersionSnapshot:
    """What one history entry records: the post state before the write."""

    post_id: str
    title: str | None
    excerpt: str | None
    content: dict[str, object]
    author_id: str | None
    change_summary: str


def _last_number(history: list[dict[str, object]]) -> int:
    numbers = [int(str(entry.get(KEY_VERSION_NUMBER) or 0)) for entry in history]
    return max(numbers, default=0)


def _same_state(entry: dict[str, object], snapshot: VersionSnapshot) -> bool:
    return (
        entry.get(KEY_SNAPSHOT) == snapshot.content
        and entry.get(KEY_TITLE) == snapshot.title
        and entry.get(KEY_EXCERPT) == snapshot.excerpt
    )


def _bounded(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    if len(entries) <= BLOG_VERSION_HISTORY_MAX:
        return entries
    return [entries[0], *entries[-(BLOG_VERSION_HISTORY_MAX - 1) :]]


def append_version(
    history: object, snapshot: VersionSnapshot
) -> list[dict[str, object]]:
    """A new bounded history list: the old entries plus one numbered snapshot."""
    raw: list[object] = list(history) if isinstance(history, list) else []
    kept = [item for item in raw if isinstance(item, dict)]
    if kept and _same_state(kept[-1], snapshot):
        return kept
    entry: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "content_id": snapshot.post_id,
        "content_type": VERSION_CONTENT_TYPE_BLOG_POST,
        KEY_VERSION_NUMBER: _last_number(kept) + 1,
        KEY_TITLE: snapshot.title,
        KEY_EXCERPT: snapshot.excerpt,
        KEY_SNAPSHOT: snapshot.content,
        "change_summary": snapshot.change_summary,
        "author_id": snapshot.author_id,
        "created_at": datetime.now(UTC).isoformat(),
    }
    return _bounded([*kept, entry])


__all__ = ["VersionSnapshot", "append_version"]
