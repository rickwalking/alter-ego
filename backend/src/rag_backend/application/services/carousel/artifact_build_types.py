"""Shared types and hashing helpers for carousel artifact builds."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from rag_backend.application.services.carousel.types import unpack_extras
from rag_backend.domain.constants.artifact_build import (
    ARTIFACT_VERSION_PREFIX,
    EXPORTER_CONTRACT_VERSION,
    RENDERER_CONTRACT_VERSION,
)
from rag_backend.domain.models import CarouselProject, CarouselSlide


@dataclass(frozen=True)
class ArtifactVersionInput:
    """Canonical inputs for deterministic artifact_version hashing."""

    project_id: str
    source_lock_version: int
    presentation_policy_version: str
    presentation_policy_checksum: str | None
    template_version: str
    slides_fingerprint: str
    design_fingerprint: str | None
    creator_asset_hash: str | None
    export_width: int
    export_height: int


@dataclass(frozen=True)
class ArtifactBuildRequest:
    """Inputs for building and activating a versioned artifact."""

    project: CarouselProject
    slides: Sequence[CarouselSlide]
    source_lock_version: int
    prior_artifact_version: str | None


@dataclass(frozen=True)
class ArtifactBuildResult:
    """Outcome of artifact build and activation."""

    artifact_version: str
    operation_id: str
    lock_version: int
    manifest_path: Path
    version_dir: Path


@dataclass(frozen=True)
class ArtifactBuildFailure:
    """Failed artifact build with sanitized errors."""

    artifact_version: str
    errors: tuple[str, ...]


def compute_slides_fingerprint(slides: Sequence[CarouselSlide]) -> str:
    """Hash canonical slide payloads used for artifact versioning."""
    payload = [
        {
            "slide_number": slide.slide_number,
            "slide_type": slide.slide_type,
            "heading": slide.heading,
            "body": slide.body,
            "extras": asdict(unpack_extras(slide)),
        }
        for slide in sorted(slides, key=lambda item: item.slide_number)
    ]
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def compute_design_fingerprint(project: CarouselProject) -> str | None:
    if project.design_tokens is None:
        return None
    return sha256_text(
        json.dumps(project.design_tokens, sort_keys=True, separators=(",", ":"))
    )


def compute_artifact_version(inputs: ArtifactVersionInput) -> str:
    """Return sha256-<64 hex> artifact version from canonical JSON inputs."""
    canonical = {
        "creator_asset_hash": inputs.creator_asset_hash,
        "design_fingerprint": inputs.design_fingerprint,
        "export_height": inputs.export_height,
        "export_width": inputs.export_width,
        "exporter_contract_version": EXPORTER_CONTRACT_VERSION,
        "presentation_policy_checksum": inputs.presentation_policy_checksum,
        "presentation_policy_version": inputs.presentation_policy_version,
        "project_id": inputs.project_id,
        "renderer_contract_version": RENDERER_CONTRACT_VERSION,
        "slides_fingerprint": inputs.slides_fingerprint,
        "source_lock_version": inputs.source_lock_version,
        "template_version": inputs.template_version,
    }
    digest = sha256_text(json.dumps(canonical, sort_keys=True, separators=(",", ":")))
    return f"{ARTIFACT_VERSION_PREFIX}{digest}"


def compute_operation_id(
    project_id: str,
    source_lock_version: int,
    artifact_version: str,
) -> str:
    """Return export idempotency key sha256(project|lock|version)."""
    payload = f"{project_id}|{source_lock_version}|{artifact_version}"
    return sha256_text(payload)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "ArtifactBuildFailure",
    "ArtifactBuildRequest",
    "ArtifactBuildResult",
    "ArtifactVersionInput",
    "compute_artifact_version",
    "compute_design_fingerprint",
    "compute_operation_id",
    "compute_slides_fingerprint",
    "sha256_text",
]
