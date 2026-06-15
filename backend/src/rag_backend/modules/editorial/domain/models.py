"""Domain entities and value objects for the editorial bounded context.

The editorial context owns the 7-phase carousel editorial workflow over a
carousel project. This module defines its two new aggregates/value objects —
:class:`EditorialProject` and :class:`EditorialWorkflow` — fully typed (no
``Any``), and **re-exports** the existing carousel entities + status value
objects so existing callers keep resolving to the IDENTICAL objects.

**Re-export, not relocation (AE-0108 constraint).** ``CarouselProject``,
``CarouselSlide``, ``ResearchSource``, ``CarouselStatus`` etc. continue to live
at their legacy location ``rag_backend.domain.models`` (imported by ~50+ callers:
agents, routes, container, the workflow engine). This module re-exports them
under the module's domain namespace without moving or modifying the canonical
definitions, so identity/isinstance checks and persistence adapters keep working
during the behavior-preserving phase.

The workflow status language (phases, phase statuses, review actions) is
re-exported from :mod:`rag_backend.modules.editorial.domain.status`, which in
turn re-exports the canonical
``rag_backend.domain.constants.carousel_workflow`` constants — no new strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
    CarouselTheme,
    ResearchSource,
    ResearchSourceType,
)
from rag_backend.modules.editorial.domain.status import (
    CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
    DEFAULT_PHASE_RETRY_CAP,
    DEFAULT_REVISION_CAP_PER_PHASE,
    PHASE_BRIEF,
    PHASE_STATUS_PENDING,
)


@dataclass(frozen=True)
class EditorialWorkflow:
    """Value object describing the editorial workflow state of a project.

    Captures where a carousel project sits in the 7-phase editorial pipeline:
    the current ``phase`` and its ``phase_status`` (both drawn from the
    canonical, re-exported status language — see
    :mod:`rag_backend.modules.editorial.domain.status`), the per-phase revision
    count, and the caps that bound revisions/retries. All fields are explicitly
    typed; the phase/status strings are the canonical workflow constants.
    """

    phase: str = PHASE_BRIEF
    phase_status: str = PHASE_STATUS_PENDING
    workflow_status: str = CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT
    revision_count: int = 0
    revision_cap_per_phase: int = DEFAULT_REVISION_CAP_PER_PHASE
    phase_retry_cap: int = DEFAULT_PHASE_RETRY_CAP


@dataclass(frozen=True)
class EditorialProject:
    """The editorial aggregate: a carousel project under editorial workflow.

    Wraps the canonical :class:`CarouselProject` (re-exported, identical object)
    with its editorial :class:`EditorialWorkflow` state. This is the editorial
    context's own aggregate view; it does not modify or relocate the underlying
    carousel entity.
    """

    project: CarouselProject
    workflow: EditorialWorkflow = field(default_factory=EditorialWorkflow)

    @property
    def project_id(self) -> UUID:
        """The identifier of the underlying carousel project."""
        return self.project.id


__all__ = [
    "CarouselProject",
    "CarouselSlide",
    "CarouselStatus",
    "CarouselTheme",
    "EditorialProject",
    "EditorialWorkflow",
    "ResearchSource",
    "ResearchSourceType",
]
