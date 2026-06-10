"""Unit tests for the carousel visual QA script."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from rag_backend.application.services.carousel.visual_qa_expectations import (
    expectations_from_manifest_payload,
    expectations_from_workflow_state,
    resolve_visual_qa_expectations,
)

SCRIPT_PATH = Path(__file__).resolve().parents[4] / "scripts" / "carousel_visual_qa.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("carousel_visual_qa", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sample_manifest_payload() -> dict[str, object]:
    return {
        "project_id": "project-1",
        "artifact_version": "sha256-" + ("a" * 64),
        "presentation_policy_version": "hero_lower_third_v1",
        "presentation_policy_checksum": "sha256-" + ("b" * 64),
        "template_version": "v2",
        "renderer_contract_version": "hero_lower_third_v1",
        "exporter_contract_version": "playwright_v1",
        "source_lock_version": 1,
        "expected_slide_numbers": [1, 2, 3, 4, 5, 6, 7],
        "pt_source_hash": "pt-hash",
        "en_source_hash": "en-hash",
        "raw_image_hashes": [],
        "avatar_hash": None,
        "standard_slides_pt": [
            {
                "slide_number": 1,
                "relative_path": "pt/slide_1.jpg",
                "sha256": "hash-1",
                "width": 1080,
                "height": 1350,
            }
        ],
        "standard_slides_en": [],
        "hd_slides_pt": [
            {
                "slide_number": 1,
                "relative_path": "pt/hd/slide_1.jpg",
                "sha256": "hash-1-hd",
                "width": 2160,
                "height": 2700,
            }
        ],
        "hd_slides_en": [],
        "pdfs": [],
    }


@pytest.mark.unit
def test_validate_design_payload_requires_swipe_copy() -> None:
    script = _load_script()
    expectations = resolve_visual_qa_expectations()
    payload = {
        "layout": {"swipe_text": "Swipe \u2192"},
        "images": {
            "rendered_slides_pt": [
                f"/api/carousels/project/preview/images/slide_{index}.jpg?lang=pt"
                for index in range(1, expectations.slide_count + 1)
            ]
        },
    }

    urls = script._validate_design_payload(payload, "pt", expectations)

    assert len(urls) == expectations.slide_count


@pytest.mark.unit
def test_validate_design_payload_rejects_deslize_copy() -> None:
    script = _load_script()
    expectations = resolve_visual_qa_expectations()
    payload = {
        "layout": {"swipe_text": "Deslize \u2192"},
        "images": {"rendered_slides_pt": []},
    }

    with pytest.raises(RuntimeError, match="swipe_text"):
        script._validate_design_payload(payload, "pt", expectations)


@pytest.mark.unit
def test_jpeg_dimensions_reads_generated_image(tmp_path: Path) -> None:
    pillow = pytest.importorskip("PIL.Image")
    script = _load_script()
    image_path = tmp_path / "slide.jpg"
    image = pillow.new("RGB", (320, 400), "white")
    image.save(image_path, "JPEG")

    assert script._jpeg_dimensions(image_path) == (320, 400)


@pytest.mark.unit
def test_expectations_from_manifest_payload_uses_hd_dimensions() -> None:
    expectations = expectations_from_manifest_payload(_sample_manifest_payload())

    assert expectations.slide_count == 7
    assert expectations.expected_width == 2160
    assert expectations.expected_height == 2700
    assert expectations.artifact_version == "sha256-" + ("a" * 64)
    assert expectations.source == "manifest"


@pytest.mark.unit
def test_expectations_from_workflow_state_uses_localized_slides() -> None:
    expectations = expectations_from_workflow_state(
        {
            "localized_slides": [{"slide_index": index} for index in range(1, 8)],
            "presentation_policy_version": "hero_lower_third_v1",
            "artifact_version": "sha256-" + ("c" * 64),
        }
    )

    assert expectations is not None
    assert expectations.slide_count == 7
    assert expectations.expected_width == 2160
    assert expectations.expected_height == 2700
    assert expectations.artifact_version == "sha256-" + ("c" * 64)
    assert expectations.source == "workflow"


@pytest.mark.unit
def test_resolve_visual_qa_expectations_prefers_manifest_over_workflow() -> None:
    expectations = resolve_visual_qa_expectations(
        manifest_payload=_sample_manifest_payload(),
        workflow_payload={
            "localized_slides": [{"slide_index": 1}],
            "presentation_policy_version": "hero_lower_third_v1",
        },
    )

    assert expectations.source == "manifest"
    assert expectations.slide_count == 7


@pytest.mark.unit
def test_load_manifest_payload_reads_file(tmp_path: Path) -> None:
    script = _load_script()
    manifest_path = tmp_path / "artifact-manifest.json"
    manifest_path.write_text(json.dumps(_sample_manifest_payload()), encoding="utf-8")
    config = script.QaConfig(
        base_url="http://127.0.0.1:8000",
        project_id="project-1",
        email="qa@example.com",
        password="secret",
        output_dir=tmp_path / "output",
        manifest_path=manifest_path,
        use_hd=True,
    )

    payload = script._load_manifest_payload(config)

    assert payload is not None
    assert payload["artifact_version"] == "sha256-" + ("a" * 64)
