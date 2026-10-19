"""Pure per-row plan of the blog v1 -> v2 cutover (AE-0423, ADR-0025).

Given one ``blog_posts`` row, decide the column values ``--apply`` or
``--rollback`` writes (the DB runner only executes them):

- ``content`` — legacy rows are split to ``blog.v2``; a v2-marked row whose
  translations do not all parse keeps its PT document and loses only the bad
  translations;
- ``version_history[*].snapshot`` — every snapshot is rewritten the same way so a
  pre-cutover version can still be restored (restore is a strict v2 write);
- ``featured_image_url`` — cleared with the (null) cover of a converted legacy
  row; the old value is stashed in ``ai_generation_metadata`` (never public) and
  ``--rollback`` restores it when no cover was set since.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from rag_backend.domain.constants.blog_document import (
    CUTOVER_METADATA_KEY,
    CUTOVER_STASH_FEATURED_KEY,
    VERSION_SNAPSHOT_KEY,
)
from rag_backend.domain.models.blog_document import (
    InvalidBlogDocumentError,
    drop_invalid_translations,
    parse_blog_content,
)
from rag_backend.domain.models.blog_document_split import (
    is_v2_language_document,
    migrate_content,
    rollback_content,
)

COLUMN_CONTENT = "content"
COLUMN_FEATURED_IMAGE_URL = "featured_image_url"
COLUMN_VERSION_HISTORY = "version_history"
COLUMN_METADATA = "ai_generation_metadata"

ContentRewrite = Callable[[object], dict[str, object] | None]


@dataclass(frozen=True)
class CutoverRowState:
    """The columns of one row the cutover reads."""

    content: object
    featured_image_url: str | None
    version_history: object
    metadata: object


@dataclass(frozen=True)
class CutoverRowChange:
    """Column values to write plus what to report (the row's v2 side)."""

    values: dict[str, object]
    v2_content: dict[str, object]
    cleared_featured_image_url: str | None = None


def is_valid_v2_content(content: object) -> bool:
    """The ``--verify`` predicate: the same strict parse the read path uses."""
    try:
        parse_blog_content(content)
    except InvalidBlogDocumentError:
        return False
    return True


def apply_content(content: object) -> dict[str, object] | None:
    """The v2 rewrite of ``content`` (legacy split or translation repair)."""
    migrated = migrate_content(content)
    candidate = migrated if migrated is not None else content
    repaired = drop_invalid_translations(candidate)
    return repaired if repaired is not None else migrated


def rollback_document(content: object) -> dict[str, object] | None:
    """The v1 shape of a v2-marked ``content``, else ``None`` (no-op)."""
    if not is_v2_language_document(content):
        return None
    return rollback_content(content)


def _rewrite_entry(entry: object, rewrite: ContentRewrite) -> object:
    if not isinstance(entry, dict) or VERSION_SNAPSHOT_KEY not in entry:
        return entry
    snapshot = rewrite(entry[VERSION_SNAPSHOT_KEY])
    if snapshot is None:
        return entry
    return {**entry, VERSION_SNAPSHOT_KEY: snapshot}


def rewrite_history(history: object, rewrite: ContentRewrite) -> list[object] | None:
    """Every version snapshot rewritten, or ``None`` when nothing changed."""
    if not isinstance(history, list):
        return None
    rewritten = [_rewrite_entry(entry, rewrite) for entry in history]
    changed = any(new is not old for new, old in zip(rewritten, history, strict=True))
    return rewritten if changed else None


def _as_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _stash_featured(metadata: object, featured: str) -> dict[str, object]:
    updated = _as_dict(metadata)
    updated[CUTOVER_METADATA_KEY] = {CUTOVER_STASH_FEATURED_KEY: featured}
    return updated


def _content_values(
    row: CutoverRowState, content: dict[str, object]
) -> CutoverRowChange:
    values: dict[str, object] = {COLUMN_CONTENT: content}
    if is_v2_language_document(row.content):
        # A repaired v2 row keeps its cover, so its projection stays as is.
        return CutoverRowChange(values, content)
    values[COLUMN_FEATURED_IMAGE_URL] = None
    if not row.featured_image_url:
        return CutoverRowChange(values, content)
    values[COLUMN_METADATA] = _stash_featured(row.metadata, row.featured_image_url)
    return CutoverRowChange(values, content, row.featured_image_url)


def plan_apply(row: CutoverRowState) -> CutoverRowChange | None:
    """What ``--apply`` writes for ``row`` (``None`` = already migrated)."""
    content = apply_content(row.content)
    history = rewrite_history(row.version_history, apply_content)
    if content is None and history is None:
        return None
    change = (
        _content_values(row, content)
        if content is not None
        else CutoverRowChange({}, _as_dict(row.content))
    )
    if history is not None:
        change.values[COLUMN_VERSION_HISTORY] = history
    return change


def _stashed_featured(metadata: object) -> str | None:
    stash = _as_dict(metadata).get(CUTOVER_METADATA_KEY)
    if not isinstance(stash, dict):
        return None
    value = stash.get(CUTOVER_STASH_FEATURED_KEY)
    return value if isinstance(value, str) else None


def _restore_featured(row: CutoverRowState, values: dict[str, object]) -> None:
    metadata = _as_dict(row.metadata)
    if CUTOVER_METADATA_KEY not in metadata:
        return
    stashed = _stashed_featured(metadata)
    if stashed and not row.featured_image_url:
        values[COLUMN_FEATURED_IMAGE_URL] = stashed
    metadata.pop(CUTOVER_METADATA_KEY)
    values[COLUMN_METADATA] = metadata


def plan_rollback(row: CutoverRowState) -> CutoverRowChange | None:
    """What ``--rollback`` writes for ``row`` (``None`` = nothing to undo)."""
    content = rollback_document(row.content)
    history = rewrite_history(row.version_history, rollback_document)
    if content is None and history is None:
        return None
    values: dict[str, object] = {}
    if content is not None:
        values[COLUMN_CONTENT] = content
        _restore_featured(row, values)
    if history is not None:
        values[COLUMN_VERSION_HISTORY] = history
    return CutoverRowChange(values, _as_dict(row.content))


__all__ = [
    "COLUMN_CONTENT",
    "COLUMN_FEATURED_IMAGE_URL",
    "COLUMN_METADATA",
    "COLUMN_VERSION_HISTORY",
    "CutoverRowChange",
    "CutoverRowState",
    "apply_content",
    "is_valid_v2_content",
    "plan_apply",
    "plan_rollback",
    "rewrite_history",
    "rollback_document",
]
