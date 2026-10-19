"""Selection and report types of the AE-0426 hidden-post rebuild.

The predicate is pure and its inputs are plain facts of a ``blog_posts`` row, so
the dry run and the run share exactly one classification. Operator guard rails
(``only`` / ``limit`` / ``max_posts`` / ``allow_published``) live here too.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from rag_backend.domain.constants.blog_document import BLOG_SCHEMA_V2
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.blog_rebuild import (
    CRITERION_ALREADY_REBUILT,
    CRITERION_CURRENTLY_PUBLISHED,
    CRITERION_MARKER,
    CRITERION_V2_WITH_QUALITY,
    LOG_REBUILD_CAPPED,
    LOG_REBUILD_SKIPPED,
    OUTCOME_SKIPPED,
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RebuildCandidate:
    """A ``blog_posts`` row and the facts the selection predicate needs.

    The store reads the marker and the document in Python (small table, and the
    JSON shape is dialect-independent) so the predicate stays pure and testable.
    """

    post_id: str
    project_id: str | None
    author_id: str | None
    lock_version: int
    status: str
    has_hidden_marker: bool
    rebuilt_at: str | None
    content_schema: str | None
    voice_score: float | None


@dataclass(frozen=True)
class RebuildEntry:
    """One row in a report bucket (``detail`` = the skip reason or run status)."""

    post_id: str
    criterion: str
    detail: str | None = None


@dataclass
class RebuildReport:
    """The run summary: selected, rebuilt, skipped and failed rows (AC6)."""

    selected: list[RebuildEntry] = field(default_factory=list)
    rebuilt: list[RebuildEntry] = field(default_factory=list)
    skipped: list[RebuildEntry] = field(default_factory=list)
    failed: list[RebuildEntry] = field(default_factory=list)
    omitted: int = 0

    @property
    def counts(self) -> dict[str, int]:
        """The four summary counts, keyed by bucket name."""
        return {
            "selected": len(self.selected),
            "rebuilt": len(self.rebuilt),
            "skipped": len(self.skipped),
            "failed": len(self.failed),
        }


@dataclass(frozen=True)
class RebuildSelection:
    """Operator guard rails: which rows this invocation may touch.

    ``only`` narrows to specific post ids, ``limit`` takes the first N matching
    rows and ``max_posts`` is a hard spend cap on the rows actually processed.
    Published rows are skipped unless ``allow_published`` is explicit (a rebuild
    flips them back to ``draft``).
    """

    only: frozenset[str] = field(default_factory=frozenset)
    limit: int | None = None
    max_posts: int | None = None
    allow_published: bool = False


def selection_criterion(
    candidate: RebuildCandidate, *, allow_published: bool = False
) -> str | None:
    """Why a row is selected, why it is skipped, or ``None`` (not a candidate).

    Selection is the marker only — never ``status`` — except for a guard against
    silently unpublishing a live post: a ``published`` row is skipped unless the
    operator explicitly allows it.
    """
    if not candidate.has_hidden_marker:
        return None
    if candidate.rebuilt_at is not None:
        return CRITERION_ALREADY_REBUILT
    if candidate.status == BlogPostStatus.PUBLISHED.value and not allow_published:
        return CRITERION_CURRENTLY_PUBLISHED
    if candidate.content_schema == BLOG_SCHEMA_V2 and candidate.voice_score is not None:
        return CRITERION_V2_WITH_QUALITY
    return CRITERION_MARKER


def record_skip(report: RebuildReport, post_id: str, criterion: str) -> None:
    """Add a skip entry and emit its log event."""
    report.skipped.append(RebuildEntry(post_id, criterion, OUTCOME_SKIPPED))
    logger.info(LOG_REBUILD_SKIPPED, post_id=post_id, criterion=criterion)


def _apply_caps(
    selected: list[RebuildCandidate], selection: RebuildSelection
) -> tuple[list[RebuildCandidate], int]:
    """Apply ``limit`` then the hard ``max_posts`` cap; return omitted count."""
    omitted = 0
    for cap in (selection.limit, selection.max_posts):
        if cap is None:
            continue
        omitted += max(0, len(selected) - cap)
        selected = selected[:cap]
    return selected, omitted


def classify(
    candidates: list[RebuildCandidate], selection: RebuildSelection
) -> tuple[list[RebuildCandidate], RebuildReport]:
    """Split the rows into the operator's selection and the skip buckets."""
    report = RebuildReport()
    selected: list[RebuildCandidate] = []
    for candidate in sorted(candidates, key=lambda item: item.post_id):
        criterion = selection_criterion(
            candidate, allow_published=selection.allow_published
        )
        if criterion is None:
            continue
        if criterion == CRITERION_MARKER:
            selected.append(candidate)
            continue
        record_skip(report, candidate.post_id, criterion)
    if selection.only:
        selected = [item for item in selected if item.post_id in selection.only]
    selected, report.omitted = _apply_caps(selected, selection)
    if report.omitted:
        logger.warning(LOG_REBUILD_CAPPED, omitted=report.omitted)
    return selected, report


__all__ = [
    "RebuildCandidate",
    "RebuildEntry",
    "RebuildReport",
    "RebuildSelection",
    "classify",
    "record_skip",
    "selection_criterion",
]
