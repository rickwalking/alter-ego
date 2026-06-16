"""Concrete adapters for the presentation editorial-port surface (AE-0121).

These adapters are the infrastructure backing for the presentation forward ports
(``rag_backend.modules.presentation.domain.ports``) the EDITORIAL workflow invokes
through the public facade — and for the presentation → editorial progress
callback shim. They keep the dependency direction editorial → presentation: this
module imports NO editorial internal; it only delegates to the existing,
unchanged carousel application services so behavior is byte-identical:

* :class:`CarouselArtifactBuildAdapter` — the :class:`ArtifactBuildPort`, wrapping
  ``CarouselArtifactBuildService.build_and_activate``. The compound
  ``artifact_version`` ↔ ``lock_version`` compare-and-swap, the PDF-path stamping,
  and the design-token merge run UNCHANGED inside the wrapped service (the same
  terminal write ``editorial_finalize`` performs); the adapter only reports the
  outcome as an :class:`ArtifactActivation`.
* :class:`CarouselFormatProducer` — the carousel :class:`ContentFormatProducer`,
  wrapping the unchanged bilingual re-render (``CarouselRefinementService``); the
  single presentation-specific producer (no generic framework).
* :class:`PresentationReviewAdapter` — the :class:`PresentationReviewPort`,
  wrapping ``apply_localized_slide_edits`` / ``edited_slides_block_approval``.
* :class:`WorkflowProgressCallback` — a presentation-side helper that turns the
  injected editorial callback into the byte-identical ``phase_progress`` persist +
  SSE publish; editorial constructs it and passes it down to the image node.

Behavior-preserving: no adapter renders, bumps a lock, or stamps a column itself
beyond what the wrapped legacy path already did — each forwards to the existing
implementation, so the rendered slides/PDFs, the activation CAS, the review
re-validation, and the progress write/SSE are all untouched.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.presentation_review_edits import (
    apply_localized_slide_edits,
    edited_slides_block_approval,
)
from rag_backend.domain.models import CarouselProject, CarouselSlide
from rag_backend.modules.presentation.domain.contracts import (
    ArtifactActivation,
    ProducedArtifact,
    ProduceFormat,
    ProgressSnapshot,
)

# The single presentation format produced today (carousel). A second format adds
# a second producer, not an abstraction layer (AE-0121 non-goal).
CAROUSEL_FORMAT_NAME = "carousel"

_ERR_PROJECT_MISSING = "carousel project not found during artifact build"


class ArtifactBuildRepository(Protocol):
    """Narrow structural contract for the project/slide reads the build adapter does.

    A subset of the carousel repository port — only the two reads the artifact
    build needs. The full ``CarouselRepository`` satisfies it structurally; typing
    the adapter to this narrow surface keeps the dependency minimal and lets tests
    supply a small fake without re-implementing the whole repository.
    """

    async def get_project_by_id(self, project_id: UUID) -> CarouselProject | None:
        """Return the project, or ``None`` when absent."""
        ...

    async def get_slides_by_project(self, project_id: UUID) -> list[CarouselSlide]:
        """Return the project's slides."""
        ...


class SlideReRenderer(Protocol):
    """Narrow structural contract for the bilingual re-render the producer wraps.

    The carousel ``CarouselRefinementService`` satisfies it; typing the producer
    to this surface (rather than the concrete service) avoids an import cycle and
    lets tests inject a small fake.
    """

    async def re_render_slides(
        self,
        project_id: UUID,
        strategy: str | None = None,
    ) -> CarouselProject:
        """Re-render the project's slides/PDFs and return the updated project."""
        ...


class CarouselArtifactBuildAdapter:
    """:class:`ArtifactBuildPort` backed by the carousel artifact-build service.

    Runs the SAME stage → manifest → promote → activation-CAS path the editorial
    finalize uses today: it reads the source ``lock_version`` and the prior
    ``artifact_version``, loads the project + slides through the (re-exported)
    carousel repository port, and calls the unchanged
    ``CarouselArtifactBuildService.build_and_activate``. The compound CAS
    (``lock_version`` ↔ ``artifact_version``) and its ``+1`` bump are performed
    inside that service, byte-identically; this adapter only maps the result.
    """

    def __init__(self, db: AsyncSession, repository: ArtifactBuildRepository) -> None:
        self._db = db
        self._repository = repository

    async def build_and_activate(self, project_id: str) -> ArtifactActivation:
        """Build + activate the project's artifact via the unchanged CAS path."""
        # Lazy import: the artifact-build service transitively pulls the carousel
        # workflow graph, which imports the presentation facade — importing it at
        # module top would close an import cycle. Resolved at call time instead.
        from rag_backend.application.services.carousel.artifact_build_service import (
            ArtifactBuildFailure,
            ArtifactBuildRequest,
            CarouselArtifactBuildService,
            read_project_lock_version,
        )

        project = await self._repository.get_project_by_id(UUID(project_id))
        if project is None:
            return ArtifactActivation(ok=False, errors=(_ERR_PROJECT_MISSING,))
        source_lock_version = await read_project_lock_version(self._db, project_id)
        slides = await self._repository.get_slides_by_project(project.id)
        result = await CarouselArtifactBuildService().build_and_activate(
            self._db,
            ArtifactBuildRequest(
                project=project,
                slides=slides,
                source_lock_version=source_lock_version,
                prior_artifact_version=project.artifact_version,
            ),
        )
        if isinstance(result, ArtifactBuildFailure):
            return ArtifactActivation(
                ok=False,
                artifact_version=result.artifact_version or "",
                errors=tuple(result.errors),
            )
        return ArtifactActivation(ok=True, artifact_version=result.artifact_version)


class CarouselFormatProducer:
    """The carousel :class:`ContentFormatProducer` (the only producer today).

    Wraps the unchanged :class:`CarouselRefinementService` re-render so the
    rendered slide JPGs/PDFs and the stamped PDF-path pointers stay byte-identical.
    """

    def __init__(self, refinement: SlideReRenderer) -> None:
        self._refinement = refinement

    @property
    def format_name(self) -> str:
        """The carousel format identifier."""
        return CAROUSEL_FORMAT_NAME

    async def produce(self, command: ProduceFormat) -> ProducedArtifact:
        """Re-render the project's slides/PDFs and return the artifact pointers."""
        project = await self._refinement.re_render_slides(
            UUID(command.project_id),
            strategy=command.strategy,
        )
        return ProducedArtifact(
            format_name=CAROUSEL_FORMAT_NAME,
            pdf_path=project.pdf_path or "",
            pdf_path_en=project.pdf_path_en or "",
        )


def apply_localized_slide_edits_via_port(
    state: Mapping[str, object],
    edited_slides: list[dict[str, object]],
) -> dict[str, object]:
    """Apply reviewer slide edits via the presentation review boundary.

    The function-shaped entry point the editorial workflow nodes call through the
    presentation facade (the graph helpers are pure + un-injected, so they reach
    the presentation review surface here rather than importing the application
    service directly — keeping ``carousel = presentation only`` for the review
    path). Delegates UNCHANGED to ``apply_localized_slide_edits``.
    """
    return apply_localized_slide_edits(state, edited_slides)


class PresentationReviewAdapter:
    """:class:`PresentationReviewPort` backed by the presentation review service.

    Forwards to the unchanged ``apply_localized_slide_edits`` /
    ``edited_slides_block_approval`` so the re-validation behavior and the
    returned state-update shape stay byte-identical. Stateless — the wrapped
    functions are pure over the passed state.
    """

    @staticmethod
    def apply_slide_edits(
        state: Mapping[str, object],
        edited_slides: list[dict[str, object]],
    ) -> dict[str, object]:
        """Delegate to the unchanged ``apply_localized_slide_edits``."""
        return apply_localized_slide_edits(state, edited_slides)

    @staticmethod
    def edits_block_approval(
        state: Mapping[str, object],
        edited_slides: list[dict[str, object]],
    ) -> bool:
        """Delegate to the unchanged ``edited_slides_block_approval``."""
        return edited_slides_block_approval(state, edited_slides)


# Type of the editorial-supplied callback that performs the byte-identical
# ``phase_progress`` persist + SSE publish for a reported snapshot.
ProgressReporter = Callable[[ProgressSnapshot], Awaitable[None]]


class WorkflowProgressCallback:
    """:class:`WorkflowProgressPort` shim wrapping an editorial-supplied reporter.

    Editorial owns the workflow-state write (``phase_progress``) + the SSE
    emission; it constructs this shim with its own ``reporter`` callable and
    passes it down to the presentation image node. The node calls
    :meth:`report_progress` with a :class:`ProgressSnapshot`; this shim forwards to
    the editorial reporter, which performs the exact legacy persist + publish. The
    presentation side never imports the editorial reporter — it receives it.
    """

    def __init__(self, reporter: ProgressReporter) -> None:
        self._reporter = reporter

    async def report_progress(self, snapshot: ProgressSnapshot) -> None:
        """Forward the snapshot to the editorial reporter (persist + SSE)."""
        await self._reporter(snapshot)


__all__ = [
    "CAROUSEL_FORMAT_NAME",
    "ArtifactBuildRepository",
    "CarouselArtifactBuildAdapter",
    "CarouselFormatProducer",
    "PresentationReviewAdapter",
    "ProgressReporter",
    "SlideReRenderer",
    "WorkflowProgressCallback",
    "apply_localized_slide_edits_via_port",
]
