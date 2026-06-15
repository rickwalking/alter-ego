"""Typed structures for carousel artifact manifests.

The serialized payload models (`CarouselArtifactManifestPayload` and its nested
records) are defined module-local here as Pydantic value objects. They are the
seed of the future ``carousel_presentation`` domain (Phase 5 modularization)
and intentionally NOT placed in a shared models dump.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ERR_NON_NUMERIC = "expected a numeric value for an int manifest field"


def _to_int(value: object) -> int:
    """Coerce a numeric-like payload value to ``int``.

    Accepts ``int``/``float``/``str`` (e.g. JSON numbers serialized as strings)
    and rejects anything else with a clear ``TypeError`` so Pydantic surfaces a
    validation error instead of a silent miscast.
    """
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, (float, str)):
        return int(value)
    raise TypeError(_ERR_NON_NUMERIC)


class ArtifactSlideFileRecord(BaseModel):
    """Serialized rendered-slide file entry."""

    model_config = ConfigDict(extra="ignore")

    slide_number: int
    relative_path: str
    sha256: str
    width: int
    height: int

    @field_validator("slide_number", "width", "height", mode="before")
    @classmethod
    def _coerce_int(cls, value: object) -> int:
        return _to_int(value)

    @field_validator("relative_path", "sha256", mode="before")
    @classmethod
    def _coerce_str(cls, value: object) -> str:
        return str(value)


class ArtifactPdfRecord(BaseModel):
    """Serialized exported-PDF entry."""

    model_config = ConfigDict(extra="ignore")

    language: str
    relative_path: str
    page_count: int
    sha256: str

    @field_validator("page_count", mode="before")
    @classmethod
    def _coerce_page_count(cls, value: object) -> int:
        return _to_int(value)

    @field_validator("language", "relative_path", "sha256", mode="before")
    @classmethod
    def _coerce_str(cls, value: object) -> str:
        return str(value)


class ArtifactRawImageRecord(BaseModel):
    """Serialized raw source-image entry."""

    model_config = ConfigDict(extra="ignore")

    slide_number: int
    relative_path: str
    sha256: str

    @field_validator("slide_number", mode="before")
    @classmethod
    def _coerce_slide_number(cls, value: object) -> int:
        return _to_int(value)

    @field_validator("relative_path", "sha256", mode="before")
    @classmethod
    def _coerce_str(cls, value: object) -> str:
        return str(value)


class CarouselArtifactManifestPayload(BaseModel):
    """Serialized artifact-manifest payload with safe defaults and validators.

    Replaces the former ``TypedDict`` so callers can rely on validated, typed
    attribute access (``payload.key``) instead of unsafe ``payload["key"]``.
    """

    model_config = ConfigDict(extra="ignore")

    project_id: str
    artifact_version: str
    presentation_policy_version: str
    presentation_policy_checksum: str | None = None
    template_version: str
    renderer_contract_version: str
    exporter_contract_version: str
    source_lock_version: int
    expected_slide_numbers: list[int] = Field(default_factory=list)
    pt_source_hash: str
    en_source_hash: str
    raw_image_hashes: list[ArtifactRawImageRecord] = Field(default_factory=list)
    avatar_hash: str | None = None
    standard_slides_pt: list[ArtifactSlideFileRecord] = Field(default_factory=list)
    standard_slides_en: list[ArtifactSlideFileRecord] = Field(default_factory=list)
    hd_slides_pt: list[ArtifactSlideFileRecord] = Field(default_factory=list)
    hd_slides_en: list[ArtifactSlideFileRecord] = Field(default_factory=list)
    pdfs: list[ArtifactPdfRecord] = Field(default_factory=list)

    @field_validator(
        "project_id",
        "artifact_version",
        "presentation_policy_version",
        "template_version",
        "renderer_contract_version",
        "exporter_contract_version",
        "pt_source_hash",
        "en_source_hash",
        mode="before",
    )
    @classmethod
    def _coerce_required_str(cls, value: object) -> str:
        return str(value)

    @field_validator("source_lock_version", mode="before")
    @classmethod
    def _coerce_source_lock_version(cls, value: object) -> int:
        return _to_int(value)

    @field_validator(
        "expected_slide_numbers",
        "raw_image_hashes",
        "standard_slides_pt",
        "standard_slides_en",
        "hd_slides_pt",
        "hd_slides_en",
        "pdfs",
        mode="before",
    )
    @classmethod
    def _default_empty_list(cls, value: object) -> object:
        """Treat a missing/None collection as an empty list."""
        if value is None:
            return []
        return value


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
    standard_slides_pt: tuple[ArtifactSlideFileEntry, ...] = field(
        default_factory=tuple
    )
    standard_slides_en: tuple[ArtifactSlideFileEntry, ...] = field(
        default_factory=tuple
    )
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
            standard_slides_pt=_slide_records(self.standard_slides_pt),
            standard_slides_en=_slide_records(self.standard_slides_en),
            hd_slides_pt=_slide_records(self.hd_slides_pt),
            hd_slides_en=_slide_records(self.hd_slides_en),
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


def manifest_from_payload(
    payload: CarouselArtifactManifestPayload,
) -> CarouselArtifactManifest:
    """Build a manifest dataclass from a validated manifest payload."""
    return CarouselArtifactManifest(
        project_id=payload.project_id,
        artifact_version=payload.artifact_version,
        presentation_policy_version=payload.presentation_policy_version,
        presentation_policy_checksum=payload.presentation_policy_checksum,
        template_version=payload.template_version,
        renderer_contract_version=payload.renderer_contract_version,
        exporter_contract_version=payload.exporter_contract_version,
        source_lock_version=payload.source_lock_version,
        expected_slide_numbers=tuple(payload.expected_slide_numbers),
        pt_source_hash=payload.pt_source_hash,
        en_source_hash=payload.en_source_hash,
        raw_image_hashes=tuple(
            ArtifactRawImageEntry(
                slide_number=entry.slide_number,
                relative_path=entry.relative_path,
                sha256=entry.sha256,
            )
            for entry in payload.raw_image_hashes
        ),
        avatar_hash=payload.avatar_hash,
        standard_slides_pt=_slide_entries(payload.standard_slides_pt),
        standard_slides_en=_slide_entries(payload.standard_slides_en),
        hd_slides_pt=_slide_entries(payload.hd_slides_pt),
        hd_slides_en=_slide_entries(payload.hd_slides_en),
        pdfs=tuple(
            ArtifactPdfEntry(
                language=entry.language,
                relative_path=entry.relative_path,
                page_count=entry.page_count,
                sha256=entry.sha256,
            )
            for entry in payload.pdfs
        ),
    )


def _slide_records(
    entries: tuple[ArtifactSlideFileEntry, ...],
) -> list[ArtifactSlideFileRecord]:
    """Convert slide file entries to slide file records."""
    return [
        ArtifactSlideFileRecord(
            slide_number=entry.slide_number,
            relative_path=entry.relative_path,
            sha256=entry.sha256,
            width=entry.width,
            height=entry.height,
        )
        for entry in entries
    ]


def _slide_entries(
    records: list[ArtifactSlideFileRecord],
) -> tuple[ArtifactSlideFileEntry, ...]:
    return tuple(
        ArtifactSlideFileEntry(
            slide_number=record.slide_number,
            relative_path=record.relative_path,
            sha256=record.sha256,
            width=record.width,
            height=record.height,
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
