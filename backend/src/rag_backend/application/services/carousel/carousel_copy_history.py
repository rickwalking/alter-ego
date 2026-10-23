"""Which versions one caption / LinkedIn save records.

A save records, per text it changed, the new text by its author. When the text
it replaced is not the newest stored version of that field (the generated text,
or one another writer such as the chat refine or a distribution regeneration
left), that text is recorded first, without an author, so it can be restored. A
text the save did not change records nothing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.domain.constants.carousel_copy_versions import (
    SUMMARY_EDIT,
    SUMMARY_PREVIOUS,
    SUMMARY_RESTORE,
)
from rag_backend.domain.constants.distribution import DISTRIBUTION_KEYS
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.carousel_copy_version import NewCopyVersion


@dataclass(frozen=True)
class CopyChange:
    """The texts before and after one save, who saved, and what it restored."""

    before: Mapping[str, str | None]
    after: Mapping[str, str | None]
    author_id: str | None
    restored_from: int | None = None


def copy_texts(project: CarouselProject) -> dict[str, str | None]:
    """The caption and LinkedIn posts of ``project`` by API field name."""
    return {field: getattr(project, field) for field in DISTRIBUTION_KEYS}


def _edit(change: CopyChange, field: str, text: str) -> NewCopyVersion:
    restored = change.restored_from is not None
    return NewCopyVersion(
        field=field,
        text=text,
        author_id=change.author_id,
        summary=SUMMARY_RESTORE if restored else SUMMARY_EDIT,
        restored_from=change.restored_from,
    )


def _previous(field: str, text: str) -> NewCopyVersion:
    return NewCopyVersion(
        field=field, text=text, author_id=None, summary=SUMMARY_PREVIOUS
    )


def versions_for_change(
    change: CopyChange, latest: Mapping[str, str]
) -> list[NewCopyVersion]:
    """The versions to record, oldest first, for the texts ``change`` changed.

    ``latest`` is the newest stored text of each field that has versions.
    """
    versions: list[NewCopyVersion] = []
    for field in DISTRIBUTION_KEYS:
        old, new = change.before.get(field), change.after.get(field)
        if new is None or new == old:
            continue
        if old and latest.get(field) != old:
            versions.append(_previous(field, old))
        versions.append(_edit(change, field, new))
    return versions


__all__ = ["CopyChange", "copy_texts", "versions_for_change"]
