"""Version snapshots of a blog post (AE-0424, F-13).

Every content save (PUT, restore, image/rewrite/translation writes) appends one
entry to ``blog_posts.version_history`` in the same transaction as the write,
so history is no longer written only by restore (the old chicken-and-egg). An
entry snapshots the **saved** state: title, excerpt and the ``blog.v2`` content.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from rag_backend.domain.constants.blog_editor import VERSION_CONTENT_TYPE_BLOG_POST

KEY_VERSION_NUMBER = "version_number"


@dataclass(frozen=True)
class VersionSnapshot:
    """What one history entry records (the state after the write)."""

    post_id: str
    title: str | None
    excerpt: str | None
    content: dict[str, object]
    author_id: str | None
    change_summary: str


def _last_number(history: list[object]) -> int:
    numbers = [
        int(entry.get(KEY_VERSION_NUMBER, 0) or 0)
        for entry in history
        if isinstance(entry, dict)
    ]
    return max(numbers, default=0)


def append_version(
    history: object, snapshot: VersionSnapshot
) -> list[dict[str, object]]:
    """A new history list: the old entries plus one numbered snapshot."""
    entries: list[object] = list(history) if isinstance(history, list) else []
    entry: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "content_id": snapshot.post_id,
        "content_type": VERSION_CONTENT_TYPE_BLOG_POST,
        KEY_VERSION_NUMBER: _last_number(entries) + 1,
        "title": snapshot.title,
        "excerpt": snapshot.excerpt,
        "snapshot": snapshot.content,
        "change_summary": snapshot.change_summary,
        "author_id": snapshot.author_id,
        "created_at": datetime.now(UTC).isoformat(),
    }
    kept = [item for item in entries if isinstance(item, dict)]
    return [*kept, entry]


__all__ = ["VersionSnapshot", "append_version"]
