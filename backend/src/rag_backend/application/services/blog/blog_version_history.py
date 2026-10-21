"""Version snapshots of a blog post.

Every content write (PUT, restore, image/rewrite/translation writes) appends one
entry to ``blog_posts.version_history`` in the same transaction as the write.
An entry snapshots the state **before** the write (title, excerpt, ``blog.v2``
content), so the first save keeps the original (e.g. AI-written) draft and any
earlier state can be restored. History is bounded: the first entry (the
original draft) is always kept plus the most recent ones, up to
``BLOG_VERSION_HISTORY_MAX``. A write whose pre-state equals the newest entry
adds nothing.

An **empty** document (the generation bootstrap or a cleared
document) is never snapshotted — the generation's first write would otherwise
store the empty bootstrap as version 1, kept forever as "the original draft",
and restoring it 422s. Skipping it makes the first appended entry the first
stored AI draft. :func:`drop_empty_entries` is the repair for history written
before this rule (used by the operator command ``blog_empty_versions``).
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
KEY_SECTIONS = "sections"
KEY_COVER = "cover"
KEY_QUALITY = "quality"
KEY_TRANSLATIONS = "translations"
KEY_BODY_MD = "body_md"
KEY_HEADING = "heading"
KEY_IMAGE = "image"


def _empty_language(document: object) -> bool:
    """True when one language document holds no readable content."""
    if not isinstance(document, dict):
        return True
    sections = document.get(KEY_SECTIONS)
    if not isinstance(sections, list):
        return True
    for section in sections:
        if not isinstance(section, dict):
            continue
        for field in (KEY_BODY_MD, KEY_HEADING):
            if isinstance(section.get(field), str) and section[field].strip():
                return False
        if section.get(KEY_IMAGE) is not None:
            return False
    return True


def is_empty_document(content: object) -> bool:
    """True when a snapshot holds no content: the bootstrap or a cleared doc.

    Restoring such a snapshot would 422 (zero sections), so it is never worth
    keeping in the history.
    """
    if not isinstance(content, dict):
        return True
    if content.get(KEY_COVER) is not None:
        return False
    if content.get(KEY_QUALITY) is not None:
        return False
    translations = content.get(KEY_TRANSLATIONS)
    if isinstance(translations, dict) and any(
        not _empty_language(document) for document in translations.values()
    ):
        return False
    return _empty_language(content)


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
    """A new bounded history list: the old entries plus one numbered snapshot.

    An empty snapshot adds nothing: the generation's first
    write must not capture the empty bootstrap, so the first entry becomes the
    first stored AI draft.
    """
    raw: list[object] = list(history) if isinstance(history, list) else []
    kept = [item for item in raw if isinstance(item, dict)]
    if is_empty_document(snapshot.content):
        return kept
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


def drop_empty_entries(history: object) -> list[dict[str, object]] | None:
    """The history without empty snapshots, renumbered 1..N; ``None`` when clean.

    The one-shot repair for older history: leading bootstrap
    snapshots are dropped so the first stored AI draft becomes version 1.
    """
    raw: list[object] = list(history) if isinstance(history, list) else []
    kept = [item for item in raw if isinstance(item, dict)]
    cleaned = [
        entry for entry in kept if not is_empty_document(entry.get(KEY_SNAPSHOT))
    ]
    if len(cleaned) == len(kept):
        return None
    return [
        {**entry, KEY_VERSION_NUMBER: index}
        for index, entry in enumerate(cleaned, start=1)
    ]


__all__ = [
    "VersionSnapshot",
    "append_version",
    "drop_empty_entries",
    "is_empty_document",
]
