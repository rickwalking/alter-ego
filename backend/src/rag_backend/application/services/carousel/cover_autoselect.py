"""Use the cover the autopilot generated for a fresh carousel on slide 1.

Called only after the autopilot-started generation settled ``succeeded``.
The selection waits (bounded) until the workflow is paused at a gate, so no
running phase holds a stale copy of the project that would write the old
cover back, then stores the generated asset as ``slide_cover`` through the
lock-version CAS. It never re-renders, never changes the carousel status and
never publishes: the finalize render of the workflow uses the stored cover,
and the owner reviews it like any other slide 1.

The owner's choice always wins: a cover chosen before the job was scheduled,
or any change to ``slide_cover`` / ``hook_asset_id`` since, is a logged skip.
A carousel that already reached the owner's review (completed or at
``final_review``) is skipped too; the cover stays a picker option. A CAS
conflict or a held lock is a logged skip, never retried.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

import structlog

from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_REJECTED,
)
from rag_backend.domain.constants.cover_autoselect import (
    AUTO_SELECT_MAX_WAIT_SECONDS,
    AUTO_SELECT_POLL_SECONDS,
    LOG_COVER_AUTO_SELECT,
    OUTCOME_AUTO_SELECT_ALREADY,
    OUTCOME_AUTO_SELECT_SELECTED,
    OUTCOME_AUTO_SELECT_SKIPPED,
    REASON_AUTO_SELECT_COMPLETED,
    REASON_AUTO_SELECT_CONFLICT,
    REASON_AUTO_SELECT_FAILED,
    REASON_AUTO_SELECT_MANUAL_CHOICE,
    REASON_AUTO_SELECT_NO_PROJECT,
    REASON_AUTO_SELECT_NO_RESULT,
    REASON_AUTO_SELECT_OWNER_COVER,
    REASON_AUTO_SELECT_TIMED_OUT,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, kw_only=True)
class CoverBaseline:
    """Slide 1's cover fields when the generation was scheduled."""

    slide_cover_asset_id: UUID | None
    hook_asset_id: UUID | None


def cover_baseline(project: CarouselProject) -> CoverBaseline:
    """The cover fields of ``project`` as they are now."""
    cover = project.slide_cover
    return CoverBaseline(
        slide_cover_asset_id=cover.asset_id if cover is not None else None,
        hook_asset_id=project.hook_asset_id,
    )


@dataclass(frozen=True, kw_only=True)
class AutoCoverSelection:
    """The carousel, the succeeded generation and the scheduling baseline."""

    project_id: str
    generation_id: UUID
    baseline: CoverBaseline


@dataclass(frozen=True, kw_only=True)
class ProjectAtVersion:
    """A fresh read of the project and the lock version it was read at."""

    project: CarouselProject
    lock_version: int


@dataclass(frozen=True, kw_only=True)
class AutoCoverWrite:
    """Store ``asset_id`` as slide 1's cover at ``expected_version``."""

    project_id: str
    asset_id: UUID
    expected_version: int
    baseline: CoverBaseline


class AutoCoverStore(Protocol):
    """Fresh reads and the CAS write (each call on its own session)."""

    async def result_asset(self, generation_id: UUID) -> UUID | None:
        """The asset a succeeded generation stored, else None."""
        ...

    async def load(self, project_id: str) -> ProjectAtVersion | None:
        """The project as committed now, or None when it is gone."""
        ...

    async def write(self, command: AutoCoverWrite) -> str:
        """``AUTOFIX_STATUS_*`` of the switch, or a ``REASON_*`` refusal."""
        ...


@dataclass(frozen=True, kw_only=True)
class AutoCoverPolling:
    """How often and how long to wait for the workflow to pause at a gate."""

    interval_seconds: float = AUTO_SELECT_POLL_SECONDS
    max_wait_seconds: float = AUTO_SELECT_MAX_WAIT_SECONDS
    sleep: Callable[[float], Awaitable[None]] = field(default=asyncio.sleep)


def choice_refusal(
    project: CarouselProject, baseline: CoverBaseline, asset_id: UUID
) -> str | None:
    """Why the generated cover must not replace slide 1's cover, if any."""
    cover = project.slide_cover
    if cover is not None and cover.asset_id == asset_id:
        return OUTCOME_AUTO_SELECT_ALREADY
    if baseline.slide_cover_asset_id is not None:
        return REASON_AUTO_SELECT_OWNER_COVER
    if cover_baseline(project) != baseline:
        return REASON_AUTO_SELECT_MANUAL_CHOICE
    return None


def _phase_refusal(project: CarouselProject) -> str | None:
    """The owner's review already started, or the carousel or phase ended."""
    if project.status == CarouselStatus.FAILED:
        return REASON_AUTO_SELECT_FAILED
    if project.status == CarouselStatus.COMPLETED:
        return REASON_AUTO_SELECT_COMPLETED
    if project.current_phase == PHASE_FINAL_REVIEW:
        return REASON_AUTO_SELECT_COMPLETED
    if project.phase_status in _ENDED_PHASE_STATUSES:
        return REASON_AUTO_SELECT_FAILED
    return None


_ENDED_PHASE_STATUSES = frozenset({PHASE_STATUS_REJECTED, PHASE_STATUS_FAILED})


_WRITE_REFUSALS: dict[str, str] = {
    AUTOFIX_STATUS_CONFLICT: REASON_AUTO_SELECT_CONFLICT,
}


_WARNING_REASONS = frozenset(
    {
        REASON_AUTO_SELECT_NO_RESULT,
        REASON_AUTO_SELECT_NO_PROJECT,
        REASON_AUTO_SELECT_TIMED_OUT,
    }
)


def _log(selection: AutoCoverSelection, outcome: str, reason: str = "") -> str:
    """Log the outcome; a lost row or a wait that ran out is a warning."""
    log = logger.warning if reason in _WARNING_REASONS else logger.info
    log(
        LOG_COVER_AUTO_SELECT,
        outcome=outcome,
        reason=reason,
        project_id=selection.project_id,
        generation_id=str(selection.generation_id),
    )
    return reason or outcome


def _skip(selection: AutoCoverSelection, reason: str) -> str:
    return _log(selection, OUTCOME_AUTO_SELECT_SKIPPED, reason)


class AutoCoverSelector:
    """Store a succeeded autopilot cover as slide 1's cover, when allowed."""

    def __init__(
        self, store: AutoCoverStore, polling: AutoCoverPolling | None = None
    ) -> None:
        self._store = store
        self._polling = polling or AutoCoverPolling()

    async def select(self, selection: AutoCoverSelection) -> str:
        """``selected`` / ``already_selected``, or the skip reason."""
        asset_id = await self._store.result_asset(selection.generation_id)
        if asset_id is None:
            return _skip(selection, REASON_AUTO_SELECT_NO_RESULT)
        found = await self._paused(selection.project_id)
        if isinstance(found, str):
            return _skip(selection, found)
        refusal = choice_refusal(found.project, selection.baseline, asset_id)
        if refusal == OUTCOME_AUTO_SELECT_ALREADY:
            return _log(selection, refusal)
        if refusal is not None:
            return _skip(selection, refusal)
        status = await self._store.write(
            AutoCoverWrite(
                project_id=selection.project_id,
                asset_id=asset_id,
                expected_version=found.lock_version,
                baseline=selection.baseline,
            )
        )
        return self._settle(selection, status)

    @staticmethod
    def _settle(selection: AutoCoverSelection, status: str) -> str:
        if status == AUTOFIX_STATUS_FIXED:
            return _log(selection, OUTCOME_AUTO_SELECT_SELECTED)
        return _skip(selection, _WRITE_REFUSALS.get(status, status))

    async def _paused(self, project_id: str) -> ProjectAtVersion | str:
        """The project once paused at a gate, or why the wait ended."""
        waited = 0.0
        while True:
            found = await self._store.load(project_id)
            if found is None:
                return REASON_AUTO_SELECT_NO_PROJECT
            refusal = _phase_refusal(found.project)
            if refusal is not None:
                return refusal
            if found.project.phase_status != PHASE_STATUS_IN_PROGRESS:
                return found
            if waited >= self._polling.max_wait_seconds:
                return REASON_AUTO_SELECT_TIMED_OUT
            await self._polling.sleep(self._polling.interval_seconds)
            waited += self._polling.interval_seconds


__all__ = [
    "AutoCoverPolling",
    "AutoCoverSelection",
    "AutoCoverSelector",
    "AutoCoverStore",
    "AutoCoverWrite",
    "CoverBaseline",
    "ProjectAtVersion",
    "choice_refusal",
    "cover_baseline",
]
