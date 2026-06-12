"""Unit tests for null-safe artifact manifest building.

Feature: Null-Safe Manifest Building (see features/carousel_null_safety.feature)

  Scenario: manifest_from_payload with missing optional field
    Given a payload missing the policy_version field
    When manifest_from_payload is called
    Then policy_version is None in the result

  Scenario: manifest_from_payload with invalid raw_image_hashes
    Given a payload with raw_image_hashes=None
    When manifest_from_payload is called
    Then raw_image_hashes is an empty list in the result
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rag_backend.application.services.carousel.artifact_manifest import (
    ArtifactRawImageEntry,
    CarouselArtifactManifestPayload,
    manifest_from_payload,
)


def _base_payload() -> dict[str, object]:
    """Return a minimal valid serialized manifest payload."""
    return {
        "project_id": "proj-1",
        "artifact_version": "v1",
        "presentation_policy_version": "policy-v1",
        "presentation_policy_checksum": "checksum-abc",
        "template_version": "tpl-1",
        "renderer_contract_version": "rc-1",
        "exporter_contract_version": "ec-1",
        "source_lock_version": 3,
        "expected_slide_numbers": [1, 2, 3],
        "pt_source_hash": "pt-hash",
        "en_source_hash": "en-hash",
        "raw_image_hashes": [
            {
                "slide_number": 1,
                "relative_path": "raw/1.png",
                "sha256": "rawsha",
            }
        ],
    }


@pytest.mark.unit
class TestManifestNullSafety:
    def test_missing_optional_field_is_none(self) -> None:
        # Scenario: manifest_from_payload with missing optional field
        raw = _base_payload()
        del raw["presentation_policy_checksum"]
        payload = CarouselArtifactManifestPayload.model_validate(raw)
        manifest = manifest_from_payload(payload)
        assert manifest.presentation_policy_checksum is None

    def test_missing_avatar_hash_is_none(self) -> None:
        # Scenario: manifest_from_payload with missing optional field (avatar)
        payload = CarouselArtifactManifestPayload.model_validate(_base_payload())
        manifest = manifest_from_payload(payload)
        assert manifest.avatar_hash is None

    def test_raw_image_hashes_none_becomes_empty_list(self) -> None:
        # Scenario: manifest_from_payload with invalid raw_image_hashes
        raw = _base_payload()
        raw["raw_image_hashes"] = None
        payload = CarouselArtifactManifestPayload.model_validate(raw)
        manifest = manifest_from_payload(payload)
        assert manifest.raw_image_hashes == ()

    def test_missing_collections_default_to_empty(self) -> None:
        # Scenario: missing optional collection fields default to empty tuples
        raw = _base_payload()
        del raw["raw_image_hashes"]
        payload = CarouselArtifactManifestPayload.model_validate(raw)
        manifest = manifest_from_payload(payload)
        assert manifest.raw_image_hashes == ()
        assert manifest.standard_slides_pt == ()
        assert manifest.pdfs == ()

    def test_populated_raw_image_hashes_are_typed_entries(self) -> None:
        payload = CarouselArtifactManifestPayload.model_validate(_base_payload())
        manifest = manifest_from_payload(payload)
        assert manifest.raw_image_hashes == (
            ArtifactRawImageEntry(
                slide_number=1,
                relative_path="raw/1.png",
                sha256="rawsha",
            ),
        )

    def test_numeric_strings_are_coerced(self) -> None:
        # field_validator coerces JSON numbers serialized as strings.
        raw = _base_payload()
        raw["source_lock_version"] = "7"
        raw["expected_slide_numbers"] = ["1", "2"]
        payload = CarouselArtifactManifestPayload.model_validate(raw)
        manifest = manifest_from_payload(payload)
        assert manifest.source_lock_version == 7
        assert manifest.expected_slide_numbers == (1, 2)

    def test_invalid_numeric_field_raises_validation_error(self) -> None:
        raw = _base_payload()
        raw["source_lock_version"] = "not-a-number"
        with pytest.raises(ValidationError):
            CarouselArtifactManifestPayload.model_validate(raw)

    def test_missing_required_field_raises_validation_error(self) -> None:
        raw = _base_payload()
        del raw["project_id"]
        with pytest.raises(ValidationError):
            CarouselArtifactManifestPayload.model_validate(raw)

    def test_round_trip_payload_preserves_values(self) -> None:
        payload = CarouselArtifactManifestPayload.model_validate(_base_payload())
        manifest = manifest_from_payload(payload)
        round_tripped = manifest.to_payload()
        assert round_tripped.project_id == "proj-1"
        assert round_tripped.source_lock_version == 3
        assert round_tripped.expected_slide_numbers == [1, 2, 3]
        assert round_tripped.raw_image_hashes[0].sha256 == "rawsha"
