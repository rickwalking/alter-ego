"""Rebuild AE-0422's hidden carousel-origin posts as v2 drafts (AE-0426).

The AE-0422 hide wrote ``ai_generation_metadata.hidden_bad_post`` and flipped the
row to ``draft``; this one-off operation selects by that **durable marker** (a
status selector would immediately go empty), rebuilds the row's content through
the AE-0425 writer pipeline and leaves it a ``draft`` for owner review.

The service is pure orchestration over two ports:

* :class:`RebuildStore` — the candidate rows and the two fenced row writes
  (start an attempt, stamp ``hidden_bad_post.rebuilt_at``).
* :class:`CarouselMaterialSource` — the carousel inputs + persona of a row
  (``None`` when the carousel no longer exists).

Idempotency: a row whose marker carries ``rebuilt_at`` is skipped, as is a row
already at ``blog.v2`` with a stored voice score. A rebuild reuses the existing
``blog_posts`` row (never creates a second row per project) and a ``failed``
generation leaves ``rebuilt_at`` unset so the next run retries it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Protocol

import structlog

from rag_backend.application.services.blog.blog_brief import (
    CarouselMaterial,
    carousel_brief,
    notes_material,
)
from rag_backend.application.services.blog.blog_generation_service import (
    GenerationJob,
)
from rag_backend.application.services.blog.blog_rebuild_selection import (
    RebuildCandidate,
    RebuildEntry,
    RebuildReport,
    RebuildSelection,
    classify,
    record_skip,
    selection_criterion,
)
from rag_backend.domain.constants.blog_generation import (
    GENERATION_KIND_FROM_CAROUSEL,
    LANGUAGE_PT,
    REQUEST_KEY_LANGUAGE,
    REQUEST_KEY_PERSONA_ID,
    REQUEST_KEY_PROJECT_ID,
)
from rag_backend.domain.constants.blog_rebuild import (
    CRITERION_MARKER,
    CRITERION_MISSING_CAROUSEL,
    CRITERION_MISSING_NOTES,
    LOG_REBUILD_FAILED,
    LOG_REBUILD_FINISHED,
    LOG_REBUILD_SUMMARY,
    OUTCOME_FAILED,
    OUTCOME_REBUILT,
    REBUILD_ACTOR,
    REBUILT_OUTCOMES,
)
from rag_backend.domain.models.blog_generation import (
    GenerationLease,
    GenerationOutcome,
    GenerationTrace,
)
from rag_backend.domain.models.blog_generation_state import GenerationStart
from rag_backend.domain.models.persona import PersonaProfile

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class AttemptSpec:
    """Start a rebuild attempt on an existing row (CAS on ``seen_lock_version``)."""

    post_id: str
    seen_lock_version: int
    start: GenerationStart
    allow_published: bool = False


@dataclass(frozen=True)
class RebuiltStamp:
    """The completion stamp written into ``hidden_bad_post.rebuilt_at``."""

    post_id: str
    at: str
    status: str


class RebuildStore(Protocol):
    """The rows of the rebuild and its two fenced writes."""

    async def candidates(self) -> list[RebuildCandidate]:
        """Every row carrying the AE-0422 marker (rebuilt or not)."""
        ...

    async def start_attempt(self, spec: AttemptSpec) -> GenerationLease | None:
        """Draft + fresh lease on the same row; ``None`` when it moved meanwhile."""
        ...

    async def mark_rebuilt(self, stamp: RebuiltStamp) -> None:
        """Stamp ``hidden_bad_post.rebuilt_at`` (the marker stays for audit)."""
        ...


class CarouselMaterialSource(Protocol):
    """Loads a row's carousel inputs; ``None`` when the carousel is gone."""

    async def load(self, candidate: RebuildCandidate) -> CarouselMaterial | None:
        """The carousel brief material of the candidate, or ``None``."""
        ...


class GenerationRunner(Protocol):
    """The AE-0425 run (``BlogGenerationService`` satisfies it)."""

    async def run(self, job: GenerationJob) -> GenerationOutcome | None:
        """Run one job to its recorded outcome."""
        ...


@dataclass(frozen=True)
class RebuildDeps:
    """Collaborators + deterministic clock/lease ids (tests inject both)."""

    store: RebuildStore
    materials: CarouselMaterialSource
    service_factory: Callable[[PersonaProfile, str], GenerationRunner]
    clock: Callable[[], str]
    new_lease: Callable[[], str]


@dataclass(frozen=True)
class _Ready:
    """A candidate whose carousel has the free material a paid run needs."""

    candidate: RebuildCandidate
    material: CarouselMaterial
    allow_published: bool = False


class BlogRebuildService:
    """Select, rebuild and stamp the hidden carousel-origin posts."""

    def __init__(self, deps: RebuildDeps) -> None:
        self._deps = deps

    async def preview(self, selection: RebuildSelection | None = None) -> RebuildReport:
        """Dry run: the free material checks without any LLM call.

        Missing carousels/notes are reported here exactly as a run would skip
        them, so the operator sees the true target list before paying for it.
        """
        preview_selection = replace(selection or RebuildSelection(), max_posts=None)
        ready, report = await self._prepare(preview_selection)
        report.selected = [
            RebuildEntry(item.candidate.post_id, CRITERION_MARKER) for item in ready
        ]
        return report

    async def run(self, selection: RebuildSelection | None = None) -> RebuildReport:
        """Rebuild the selected rows; one failure never aborts the run."""
        report = RebuildReport()
        try:
            ready, report = await self._prepare(selection or RebuildSelection())
            report.selected = [
                RebuildEntry(item.candidate.post_id, CRITERION_MARKER) for item in ready
            ]
            for item in ready:
                await self._rebuild(item, report)
        finally:
            logger.info(LOG_REBUILD_SUMMARY, **report.counts, omitted=report.omitted)
        return report

    async def _prepare(
        self, selection: RebuildSelection
    ) -> tuple[list[_Ready], RebuildReport]:
        selected, report = classify(await self._deps.store.candidates(), selection)
        ready: list[_Ready] = []
        for candidate in selected:
            item = await self._inspect(candidate, report)
            if item is None:
                continue
            ready.append(
                _Ready(item.candidate, item.material, selection.allow_published)
            )
        return ready, report

    async def _inspect(
        self, candidate: RebuildCandidate, report: RebuildReport
    ) -> _Ready | None:
        """Load the free material; a likely-empty brief becomes a skip."""
        try:
            material = await self._deps.materials.load(candidate)
        except Exception as exc:
            logger.exception(LOG_REBUILD_FAILED, post_id=candidate.post_id)
            report.failed.append(
                RebuildEntry(candidate.post_id, OUTCOME_FAILED, type(exc).__name__)
            )
            return None
        if material is None:
            record_skip(report, candidate.post_id, CRITERION_MISSING_CAROUSEL)
            return None
        if not notes_material(material.slides):
            record_skip(report, candidate.post_id, CRITERION_MISSING_NOTES)
            return None
        return _Ready(candidate, material)

    async def _rebuild(self, ready: _Ready, report: RebuildReport) -> None:
        candidate = ready.candidate
        post_id = candidate.post_id
        try:
            outcome = await self._attempt(ready)
            if outcome is None or outcome.status not in REBUILT_OUTCOMES:
                status = outcome.status if outcome is not None else "lease_lost"
                logger.warning(LOG_REBUILD_FAILED, post_id=post_id, status=status)
                report.failed.append(RebuildEntry(post_id, OUTCOME_FAILED, status))
                return
            await self._deps.store.mark_rebuilt(
                RebuiltStamp(
                    post_id=post_id, at=self._deps.clock(), status=outcome.status
                )
            )
        except Exception as exc:
            logger.exception(LOG_REBUILD_FAILED, post_id=post_id)
            report.failed.append(
                RebuildEntry(post_id, OUTCOME_FAILED, type(exc).__name__)
            )
            return
        report.rebuilt.append(RebuildEntry(post_id, OUTCOME_REBUILT, outcome.status))
        logger.info(LOG_REBUILD_FINISHED, post_id=post_id, status=outcome.status)

    async def _attempt(self, ready: _Ready) -> GenerationOutcome | None:
        candidate = ready.candidate
        brief = carousel_brief(ready.material)
        start = GenerationStart(
            kind=GENERATION_KIND_FROM_CAROUSEL,
            lease_id=self._deps.new_lease(),
            now=self._deps.clock(),
            request={
                REQUEST_KEY_PROJECT_ID: candidate.project_id,
                REQUEST_KEY_PERSONA_ID: None,
                REQUEST_KEY_LANGUAGE: LANGUAGE_PT,
            },
            image_slots=brief.section_count + 1,
        )
        lease = await self._deps.store.start_attempt(
            AttemptSpec(
                post_id=candidate.post_id,
                seen_lock_version=candidate.lock_version,
                start=start,
                allow_published=ready.allow_published,
            )
        )
        if lease is None:
            return None
        user_id = candidate.author_id or REBUILD_ACTOR
        service = self._deps.service_factory(ready.material.persona, user_id)
        return await service.run(
            GenerationJob(
                lease=lease,
                brief=brief,
                trace=GenerationTrace(
                    project_id=candidate.project_id or candidate.post_id,
                    user_id=user_id,
                    post_id=candidate.post_id,
                ),
                retitle=True,
            )
        )


__all__ = [
    "AttemptSpec",
    "BlogRebuildService",
    "CarouselMaterialSource",
    "GenerationRunner",
    "RebuildCandidate",
    "RebuildDeps",
    "RebuildEntry",
    "RebuildReport",
    "RebuildSelection",
    "RebuildStore",
    "RebuiltStamp",
    "selection_criterion",
]
