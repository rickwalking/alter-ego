"""Resolve slide count, dimensions, and artifact version for carousel visual QA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from rag_backend.application.services.carousel.artifact_manifest import (
    CarouselArtifactManifestPayload,
    manifest_from_payload,
)
from rag_backend.application.services.carousel.presentation_policy import (
    PresentationPolicyError,
    load_presentation_policy,
)
from rag_backend.domain.constants import CAROUSEL_HEIGHT, CAROUSEL_WIDTH
from rag_backend.domain.constants.carousel_presentation import (
    CANONICAL_SLIDE_COUNT,
    LEGACY_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
)

SOURCE_MANIFEST = "manifest"
SOURCE_WORKFLOW = "workflow"
SOURCE_POLICY = "policy"
SOURCE_FALLBACK = "fallback"

HD_SCALE_FACTOR = 2
DEFAULT_DIMENSION_TOLERANCE_PX = 1
HD_DIMENSION_TOLERANCE_PX = 2


@dataclass(frozen=True)
class VisualQaExpectations:
    """Expected visual QA targets for one carousel project."""

    slide_count: int
    expected_width: int
    expected_height: int
    dimension_tolerance_px: int
    artifact_version: str | None
    presentation_policy_version: str | None
    source: str


def _policy_hd_dimensions(policy_version: str) -> tuple[int, int, int]:
    if policy_version == PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1:
        try:
            policy = load_presentation_policy(policy_version)
        except PresentationPolicyError:
            pass
        else:
            geometry = policy.geometry
            return (
                geometry.viewport_hd_width,
                geometry.viewport_hd_height,
                geometry.tolerance_hd,
            )
    if policy_version == LEGACY_PRESENTATION_POLICY_VERSION:
        return (
            CAROUSEL_WIDTH * HD_SCALE_FACTOR,
            CAROUSEL_HEIGHT * HD_SCALE_FACTOR,
            DEFAULT_DIMENSION_TOLERANCE_PX,
        )
    return (
        CAROUSEL_WIDTH * HD_SCALE_FACTOR,
        CAROUSEL_HEIGHT * HD_SCALE_FACTOR,
        HD_DIMENSION_TOLERANCE_PX,
    )


def _policy_slide_count(policy_version: str) -> int:
    if policy_version == PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1:
        try:
            return load_presentation_policy(policy_version).slide_count
        except PresentationPolicyError:
            pass
    return CANONICAL_SLIDE_COUNT


def expectations_from_manifest_payload(
    payload: dict[str, object],
    *,
    use_hd: bool = True,
) -> VisualQaExpectations:
    """Build expectations from artifact-manifest.json payload."""
    manifest = manifest_from_payload(
        cast(CarouselArtifactManifestPayload, payload),
    )
    slide_count = len(manifest.expected_slide_numbers)
    width: int
    height: int
    tolerance: int
    if use_hd and manifest.hd_slides_pt:
        width = manifest.hd_slides_pt[0].width
        height = manifest.hd_slides_pt[0].height
        tolerance = HD_DIMENSION_TOLERANCE_PX
    elif manifest.standard_slides_pt:
        width = manifest.standard_slides_pt[0].width
        height = manifest.standard_slides_pt[0].height
        tolerance = DEFAULT_DIMENSION_TOLERANCE_PX
    else:
        width, height, tolerance = _policy_hd_dimensions(
            manifest.presentation_policy_version,
        )
    return VisualQaExpectations(
        slide_count=slide_count,
        expected_width=width,
        expected_height=height,
        dimension_tolerance_px=tolerance,
        artifact_version=manifest.artifact_version,
        presentation_policy_version=manifest.presentation_policy_version,
        source=SOURCE_MANIFEST,
    )


def expectations_from_workflow_state(
    payload: dict[str, object],
    *,
    use_hd: bool = True,
) -> VisualQaExpectations | None:
    """Build expectations from editorial workflow state payload."""
    localized = payload.get("localized_slides")
    slide_drafts = payload.get("slide_drafts")
    slide_count = 0
    if isinstance(localized, list) and localized:
        slide_count = len(localized)
    elif isinstance(slide_drafts, list) and slide_drafts:
        slide_count = len(slide_drafts)
    if slide_count <= 0:
        return None

    raw_policy = payload.get("presentation_policy_version")
    policy_version = (
        str(raw_policy).strip()
        if isinstance(raw_policy, str) and raw_policy.strip()
        else DEFAULT_PRESENTATION_POLICY_VERSION
    )
    if use_hd:
        width, height, tolerance = _policy_hd_dimensions(policy_version)
    else:
        width = CAROUSEL_WIDTH
        height = CAROUSEL_HEIGHT
        tolerance = DEFAULT_DIMENSION_TOLERANCE_PX

    raw_artifact = payload.get("artifact_version")
    artifact_version = (
        str(raw_artifact).strip()
        if isinstance(raw_artifact, str) and raw_artifact.strip()
        else None
    )
    return VisualQaExpectations(
        slide_count=slide_count,
        expected_width=width,
        expected_height=height,
        dimension_tolerance_px=tolerance,
        artifact_version=artifact_version,
        presentation_policy_version=policy_version,
        source=SOURCE_WORKFLOW,
    )


def fallback_expectations(*, use_hd: bool = True) -> VisualQaExpectations:
    """Last-resort expectations when manifest and workflow state are unavailable."""
    policy_version = DEFAULT_PRESENTATION_POLICY_VERSION
    if use_hd:
        width, height, tolerance = _policy_hd_dimensions(policy_version)
    else:
        width = CAROUSEL_WIDTH
        height = CAROUSEL_HEIGHT
        tolerance = DEFAULT_DIMENSION_TOLERANCE_PX
    return VisualQaExpectations(
        slide_count=_policy_slide_count(policy_version),
        expected_width=width,
        expected_height=height,
        dimension_tolerance_px=tolerance,
        artifact_version=None,
        presentation_policy_version=policy_version,
        source=SOURCE_FALLBACK,
    )


def resolve_visual_qa_expectations(
    *,
    manifest_payload: dict[str, object] | None = None,
    workflow_payload: dict[str, object] | None = None,
    use_hd: bool = True,
) -> VisualQaExpectations:
    """Prefer manifest values, then workflow state, then typed policy defaults."""
    if manifest_payload is not None:
        try:
            return expectations_from_manifest_payload(
                manifest_payload,
                use_hd=use_hd,
            )
        except (KeyError, TypeError, ValueError):
            pass
    if workflow_payload is not None:
        from_workflow = expectations_from_workflow_state(
            workflow_payload,
            use_hd=use_hd,
        )
        if from_workflow is not None:
            return from_workflow
    return fallback_expectations(use_hd=use_hd)


__all__ = [
    "VisualQaExpectations",
    "expectations_from_manifest_payload",
    "expectations_from_workflow_state",
    "fallback_expectations",
    "resolve_visual_qa_expectations",
]
