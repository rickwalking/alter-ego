"""Typed structures for carousel artifact manifests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict


class ArtifactSlideFileRecord(TypedDict):
    slide_number: int
    relative_path: str
    sha256: str
    width: int
    height: int


class ArtifactPdfRecord(TypedDict):
    language: str
    relative_path: str
    page_count: int
    sha256: str


class ArtifactRawImageRecord(TypedDict):
    slide_number: int
    relative_path: str
    sha256: str


class CarouselArtifactManifestPayload(TypedDict):
    project_id: str
    artifact_version: str
    presentation_policy_version: str
    presentation_policy_checksum: str | None
    template_version: str
    renderer_contract_version: str
    exporter_contract_version: str
    source_lock_version: int
    expected_slide_numbers: list[int]
    pt_source_hash: str
    en_source_hash: str
    raw_image_hashes: list[ArtifactRawImageRecord]
    avatar_hash: str | None
    standard_slides_pt: list[ArtifactSlideFileRecord]
    standard_slides_en: list[ArtifactSlideFileRecord]
    hd_slides_pt: list[ArtifactSlideFileRecord]
    hd_slides_en: list[ArtifactSlideFileRecord]
    pdfs: list[ArtifactPdfRecord]


@dataclass(frozen=True)
class ArtifactSlideFileEntry:
    slide_number: int
    relative_path: str
    sha256: str
    width: int
    height: int


@dataclass(frozen=True)
class ArtifactPdfEntry:
    language: str
    relative_path: str
    page_count: int
    sha256: str


@dataclass(frozen=True)
class ArtifactRawImageEntry:
    slide_number: int
    relative_path: str
    sha256: str


@dataclass(frozen=True)
class CarouselArtifactManifest:
    project_id: str
    artifact_version: str
    presentation_policy_version: str
    presentation_policy_checksum: str | None
    template_version: str
    renderer_contract_version: str
    exporter_contract_version: str
    source_lock_version: int
    expected_slide_numbers: tuple[int, ...]
    pt_source_hash: str
    en_source_hash: str
    raw_image_hashes: tuple[ArtifactRawImageEntry, ...] = field(default_factory=tuple)
    avatar_hash: str | None = None
    standard_slides_pt: tuple[ArtifactSlideFileEntry, ...] = field(default_factory=tuple)
    standard_slides_en: tuple[ArtifactSlideFileEntry, ...] = field(default_factory=tuple)
    hd_slides_pt: tuple[ArtifactSlideFileEntry, ...] = field(default_factory=tuple)
    hd_slides_en: tuple[ArtifactSlideFileEntry, ...] = field(default_factory=tuple)
    pdfs: tuple[ArtifactPdfEntry, ...] = field(default_factory=tuple)

    def to_payload(self) -> CarouselArtifactManifestPayload:
        return CarouselArtifactManifestPayload(
            project_id=self.project_id,
            artifact_version=self.artifact_version,
            presentation_policy_version=self.presentation_policy_version,
            presentation_policy_checksum=self.presentation_policy_checksum,
            template_version=self.template_version,
            renderer_contract_version=self.renderer_contract_version,
            exporter_contract_version=self.exporter_contract_version,
            source_lock_version=self.source_lock_version,
            expected_slide_numbers=list(self.expected_slide_numbers),
            pt_source_hash=self.pt_source_hash,
            en_source_hash=self.en_source_hash,
            raw_image_hashes=[
                ArtifactRawImageRecord(
                    slide_number=entry.slide_number,
                    relative_path=entry.relative_path,
                    sha256=entry.sha256,
                )
                for entry in self.raw_image_hashes
            ],
            avatar_hash=self.avatar_hash,
            standard_slides_pt=[
                ArtifactSlideFileRecord(
                    slide_number=entry.slide_number,
                    relative_path=entry.relative_path,
                    sha256=entry.sha256,
                    width=entry.width,
                    height=entry.height,
                )
                for entry in self.standard_slides_pt
            ],
            standard_slides_en=[
                ArtifactSlideFileRecord(
                    slide_number=entry.slide_number,
                    relative_path=entry.relative_path,
                    sha256=entry.sha256,
                    width=entry.width,
                    height=entry.height,
                )
                for entry in self.standard_slides_en
            ],
            hd_slides_pt=[
                ArtifactSlideFileRecord(
                    slide_number=entry.slide_number,
                    relative_path=entry.relative_path,
                    sha256=entry.sha256,
                    width=entry.width,
                    height=entry.height,
                )
                for entry in self.hd_slides_pt
            ],
            hd_slides_en=[
                ArtifactSlideFileRecord(
                    slide_number=entry.slide_number,
                    relative_path=entry.relative_path,
                    sha256=entry.sha256,
                    width=entry.width,
                    height=entry.height,
                )
                for entry in self.hd_slides_en
            ],
            pdfs=[
                ArtifactPdfRecord(
                    language=entry.language,
                    relative_path=entry.relative_path,
                    page_count=entry.page_count,
                    sha256=entry.sha256,
                )
                for entry in self.pdfs
            ],
        )


def manifest_from_payload(payload: CarouselArtifactManifestPayload) -> CarouselArtifactManifest:
    """Build a manifest dataclass from serialized JSON payload."""
    return CarouselArtifactManifest(
        project_id=str(payload["project_id"]),
        artifact_version=str(payload["artifact_version"]),
        presentation_policy_version=str(payload["presentation_policy_version"]),
        presentation_policy_checksum=payload.get("presentation_policy_checksum"),
        template_version=str(payload["template_version"]),
        renderer_contract_version=str(payload["renderer_contract_version"]),
        exporter_contract_version=str(payload["exporter_contract_version"]),
        source_lock_version=int(payload["source_lock_version"]),
        expected_slide_numbers=tuple(int(n) for n in payload["expected_slide_numbers"]),
        pt_source_hash=str(payload["pt_source_hash"]),
        en_source_hash=str(payload["en_source_hash"]),
        raw_image_hashes=tuple(
            ArtifactRawImageEntry(
                slide_number=int(entry["slide_number"]),
                relative_path=str(entry["relative_path"]),
                sha256=str(entry["sha256"]),
            )
            for entry in payload.get("raw_image_hashes", [])
        ),
        avatar_hash=payload.get("avatar_hash"),
        standard_slides_pt=_slide_entries(payload.get("standard_slides_pt", [])),
        standard_slides_en=_slide_entries(payload.get("standard_slides_en", [])),
        hd_slides_pt=_slide_entries(payload.get("hd_slides_pt", [])),
        hd_slides_en=_slide_entries(payload.get("hd_slides_en", [])),
        pdfs=tuple(
            ArtifactPdfEntry(
                language=str(entry["language"]),
                relative_path=str(entry["relative_path"]),
                page_count=int(entry["page_count"]),
                sha256=str(entry["sha256"]),
            )
            for entry in payload.get("pdfs", [])
        ),
    )


def _slide_entries(
    records: list[ArtifactSlideFileRecord],
) -> tuple[ArtifactSlideFileEntry, ...]:
    return tuple(
        ArtifactSlideFileEntry(
            slide_number=int(record["slide_number"]),
            relative_path=str(record["relative_path"]),
            sha256=str(record["sha256"]),
            width=int(record["width"]),
            height=int(record["height"]),
        )
        for record in records
    )


__all__ = [
    "ArtifactPdfEntry",
    "ArtifactPdfRecord",
    "ArtifactRawImageEntry",
    "ArtifactRawImageRecord",
    "ArtifactSlideFileEntry",
    "ArtifactSlideFileRecord",
    "CarouselArtifactManifest",
    "CarouselArtifactManifestPayload",
    "manifest_from_payload",
]
