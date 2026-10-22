"""One stored version of a carousel's caption or LinkedIn post."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CopyVersion:
    """A version as the history shows it: which text, who wrote it and when.

    ``author_id`` / ``author_name`` are ``None`` for the generated text kept on
    the first edit; ``restored_from`` is the version a restore brought back.
    """

    version_number: int
    field: str
    text: str
    author_id: str | None
    author_name: str | None
    created_at: datetime
    restored_from: int | None = None


@dataclass(frozen=True)
class NewCopyVersion:
    """A version to store: the text of ``field`` after (or before) a save."""

    field: str
    text: str
    author_id: str | None
    summary: str
    restored_from: int | None = None


__all__ = ["CopyVersion", "NewCopyVersion"]
