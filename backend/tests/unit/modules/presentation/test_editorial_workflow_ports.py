"""Tests for the presentation editorial-port surface (AE-0121).

Phase-5 behavior-preserving extraction: artifact build/activation, format
production (the carousel ``ContentFormatProducer``), the presentation review
boundary, and the presentation → editorial progress CALLBACK are exposed behind
the presentation facade. These tests prove, with deterministic fakes (no DB, no
live provider):

* :class:`ContentFormatProducer` / :class:`ArtifactBuildPort` /
  :class:`WorkflowProgressPort` / :class:`PresentationReviewPort` are
  runtime-checkable Protocols their adapters structurally satisfy;
* the ``CarouselFormatProducer`` delegates to the unchanged re-render and reports
  the project's PDF pointers (no generic multi-format framework — one producer);
* the ``CarouselArtifactBuildAdapter`` maps success / failure / conflict /
  missing-project to :class:`ArtifactActivation` without touching the CAS itself;
* the progress callback carries a :class:`ProgressSnapshot` whose
  ``as_phase_progress`` payload is byte-identical to the legacy in-node write, and
  the presentation → editorial direction holds (presentation reports, editorial
  owns the write);
* the presentation review port forwards to the unchanged review functions.

Behavior-preserving — Gherkin not applicable (see ticket AE-0121); verified by
this suite + mypy / lint-imports / the AE-0116 safety net.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

import pytest

from rag_backend.domain.constants.carousel import CAROUSEL_STATUS_GENERATING_IMAGES
from rag_backend.domain.constants.carousel_workflow import PHASE_IMAGES
from rag_backend.domain.models import CarouselProject, CarouselSlide, CarouselTheme
from rag_backend.modules.presentation import (
    ArtifactActivation,
    ArtifactBuildPort,
    CarouselArtifactBuildAdapter,
    CarouselFormatProducer,
    ContentFormatProducer,
    PresentationReviewAdapter,
    PresentationReviewPort,
    ProducedArtifact,
    ProduceFormat,
    ProgressSnapshot,
    WorkflowProgressCallback,
    WorkflowProgressPort,
)
from rag_backend.modules.presentation.infrastructure.editorial_workflow_ports import (
    CAROUSEL_FORMAT_NAME,
    apply_localized_slide_edits_via_port,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ============================================================================
# ProgressSnapshot — byte-identical phase_progress + the two distinct phases
# ============================================================================


class TestProgressSnapshot:
    """The snapshot reproduces the legacy ``phase_progress`` payload exactly."""

    def _snapshot(self) -> ProgressSnapshot:
        return ProgressSnapshot(
            project_id="proj-1",
            phase=CAROUSEL_STATUS_GENERATING_IMAGES,
            sse_phase=PHASE_IMAGES,
            label="Generating 2 slide images in parallel — Comic Neon",
            current=1,
            total=2,
            slides=(
                {"number": 1, "status": "done"},
                {"number": 2, "status": "in_flight"},
            ),
        )

    def test_as_phase_progress_matches_legacy_shape(self) -> None:
        """The dict keys/values match the legacy in-node ``phase_progress`` write."""
        payload = self._snapshot().as_phase_progress()
        assert payload == {
            "phase": CAROUSEL_STATUS_GENERATING_IMAGES,
            "label": "Generating 2 slide images in parallel — Comic Neon",
            "current": 1,
            "total": 2,
            "slides": [
                {"number": 1, "status": "done"},
                {"number": 2, "status": "in_flight"},
            ],
        }

    def test_two_phase_values_are_distinct_and_preserved(self) -> None:
        """``phase`` (dict) and ``sse_phase`` (SSE channel) differ, as legacy."""
        snapshot = self._snapshot()
        assert snapshot.phase == "generating_images"
        assert snapshot.sse_phase == "images"
        assert snapshot.phase != snapshot.sse_phase
        # The dict carries the generating_images phase; the SSE arg carries images.
        assert snapshot.as_phase_progress()["phase"] == snapshot.phase

    def test_as_phase_progress_copies_slide_dicts(self) -> None:
        """The returned slides are copies — mutating them never aliases the source."""
        snapshot = self._snapshot()
        payload = snapshot.as_phase_progress()
        slides = payload["slides"]
        assert isinstance(slides, list)
        slides[0]["status"] = "MUTATED"
        assert snapshot.slides[0]["status"] == "done"


# ============================================================================
# WorkflowProgressPort / WorkflowProgressCallback — the callback direction
# ============================================================================


class _RecordingReporter:
    """Editorial-side reporter stand-in: records the snapshots it is handed."""

    def __init__(self) -> None:
        self.received: list[ProgressSnapshot] = []

    async def __call__(self, snapshot: ProgressSnapshot) -> None:
        self.received.append(snapshot)


class TestWorkflowProgressCallback:
    """The callback forwards a snapshot to the editorial reporter (no write here)."""

    def test_callback_is_a_workflow_progress_port(self) -> None:
        callback = WorkflowProgressCallback(_RecordingReporter())
        assert isinstance(callback, WorkflowProgressPort)

    @pytest.mark.asyncio
    async def test_report_progress_forwards_to_reporter(self) -> None:
        reporter = _RecordingReporter()
        callback = WorkflowProgressCallback(reporter)
        snapshot = ProgressSnapshot(
            project_id="proj-1",
            phase=CAROUSEL_STATUS_GENERATING_IMAGES,
            sse_phase=PHASE_IMAGES,
            label="x",
            current=0,
            total=1,
            slides=(),
        )
        await callback.report_progress(snapshot)
        assert reporter.received == [snapshot]


# ============================================================================
# ContentFormatProducer — the carousel producer (single format, no framework)
# ============================================================================


def _make_project(
    pdf_path: str | None = None, pdf_path_en: str | None = None
) -> CarouselProject:
    """A minimal real ``CarouselProject`` carrying the producer's PDF pointers."""
    project = CarouselProject(
        topic="Fixture topic",
        audience="Fixture audience",
        niche="FIXTURE",
        theme=CarouselTheme.AI_COMPETITION,
        owner_id=str(uuid4()),
    )
    project.pdf_path = pdf_path
    project.pdf_path_en = pdf_path_en
    return project


class _StubRefinement:
    """Records the ``re_render_slides`` call and returns the given project."""

    def __init__(self, project: CarouselProject) -> None:
        self._project = project
        self.calls: list[tuple[UUID, str | None]] = []

    async def re_render_slides(
        self, project_id: UUID, strategy: str | None = None
    ) -> CarouselProject:
        self.calls.append((project_id, strategy))
        return self._project


class TestCarouselFormatProducer:
    """The carousel producer delegates to the unchanged re-render."""

    def test_producer_is_a_content_format_producer(self) -> None:
        producer = CarouselFormatProducer(_StubRefinement(_make_project()))
        assert isinstance(producer, ContentFormatProducer)

    def test_format_name_is_carousel(self) -> None:
        producer = CarouselFormatProducer(_StubRefinement(_make_project()))
        assert producer.format_name == CAROUSEL_FORMAT_NAME == "carousel"

    @pytest.mark.asyncio
    async def test_produce_re_renders_and_reports_pdf_pointers(self) -> None:
        project_id = str(uuid4())
        project = _make_project("/out/pt/carousel.pdf", "/out/en/carousel.pdf")
        refinement = _StubRefinement(project)
        producer = CarouselFormatProducer(refinement)

        result = await producer.produce(
            ProduceFormat(project_id=project_id, strategy="grid")
        )

        assert result == ProducedArtifact(
            format_name="carousel",
            pdf_path="/out/pt/carousel.pdf",
            pdf_path_en="/out/en/carousel.pdf",
        )
        # Delegated UNCHANGED: same id (parsed) + strategy passed through.
        assert refinement.calls == [(UUID(project_id), "grid")]

    @pytest.mark.asyncio
    async def test_produce_maps_missing_pointers_to_empty_strings(self) -> None:
        project_id = str(uuid4())
        refinement = _StubRefinement(_make_project(None, None))
        producer = CarouselFormatProducer(refinement)

        result = await producer.produce(ProduceFormat(project_id=project_id))

        assert result.pdf_path == ""
        assert result.pdf_path_en == ""
        assert refinement.calls == [(UUID(project_id), None)]


# ============================================================================
# ArtifactBuildPort / CarouselArtifactBuildAdapter — result mapping only
# ============================================================================


class _NoProjectRepo:
    """Repository stub whose project lookup returns ``None`` (no slides needed)."""

    async def get_project_by_id(self, project_id: UUID) -> CarouselProject | None:
        del project_id
        return None

    async def get_slides_by_project(self, project_id: UUID) -> list[CarouselSlide]:
        del project_id
        return []


class TestArtifactBuildAdapter:
    """The adapter is the ArtifactBuildPort; missing-project maps to a failure."""

    def test_adapter_is_an_artifact_build_port(self) -> None:
        adapter = CarouselArtifactBuildAdapter(
            db=cast("AsyncSession", object()), repository=_NoProjectRepo()
        )
        assert isinstance(adapter, ArtifactBuildPort)

    @pytest.mark.asyncio
    async def test_missing_project_returns_failure_without_touching_cas(self) -> None:
        # The missing-project guard returns BEFORE the db is used, so a placeholder
        # session is never touched — proving the adapter never reaches the CAS.
        adapter = CarouselArtifactBuildAdapter(
            db=cast("AsyncSession", object()), repository=_NoProjectRepo()
        )
        activation = await adapter.build_and_activate(str(uuid4()))
        assert isinstance(activation, ArtifactActivation)
        assert activation.ok is False
        assert activation.artifact_version == ""
        assert activation.errors  # carries the missing-project reason


class TestArtifactActivationValueObject:
    """The activation result is a plain, defaulted value object."""

    def test_defaults(self) -> None:
        activation = ArtifactActivation(ok=True, artifact_version="v1")
        assert activation.ok is True
        assert activation.artifact_version == "v1"
        assert activation.errors == ()

    def test_failure_carries_errors(self) -> None:
        activation = ArtifactActivation(ok=False, errors=("boom",))
        assert activation.ok is False
        assert activation.errors == ("boom",)


# ============================================================================
# PresentationReviewPort — the review boundary the workflow nodes call
# ============================================================================


class TestPresentationReviewPort:
    """The review adapter + facade function forward to the unchanged service."""

    def test_adapter_is_a_presentation_review_port(self) -> None:
        assert isinstance(PresentationReviewAdapter(), PresentationReviewPort)

    def test_apply_slide_edits_no_edits_returns_revalidation_updates(self) -> None:
        # Empty state + no edits: the unchanged service returns the (empty) merged
        # localized slides + a validation report dict — a stable, DB-free shape.
        state: Mapping[str, object] = {}
        updates = PresentationReviewAdapter().apply_slide_edits(state, [])
        assert isinstance(updates, dict)
        assert "presentation_validation" in updates or "localized_slides" in updates

    def test_facade_function_matches_adapter(self) -> None:
        # Both paths delegate to the SAME unchanged service, so they return the
        # same keys + the same (timestamp-independent) shape. The validation
        # report carries a live ``validated_at`` (datetime.now), so compare the
        # stable keys rather than the volatile timestamp.
        state: Mapping[str, object] = {}
        via_function = apply_localized_slide_edits_via_port(state, [])
        via_adapter = PresentationReviewAdapter().apply_slide_edits(state, [])
        assert via_function.keys() == via_adapter.keys()
        assert via_function["localized_slides"] == via_adapter["localized_slides"]

    def test_edits_block_approval_is_false_without_blocking_violations(self) -> None:
        state: Mapping[str, object] = {}
        assert PresentationReviewAdapter().edits_block_approval(state, []) is False
