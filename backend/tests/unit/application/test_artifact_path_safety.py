"""Unit tests for carousel artifact path confinement.

Feature: Carousel artifact serving
Scenario: Unsafe slide image filenames are rejected before filesystem access
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_backend.application.services.carousel.artifact_path_safety import (
    resolve_confined_slide_image,
    sanitize_slide_image_filename,
)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("slide-1.jpg", "slide-1.jpg"),
        ("slide_2.png", "slide_2.png"),
        ("../etc/passwd", None),
        ("../../secret.jpg", None),
        ("nested/path.jpg", None),
        ("", None),
        (".", None),
        ("..", None),
        ("slide<script>.jpg", None),
    ],
)
def test_sanitize_slide_image_filename(filename: str, expected: str | None) -> None:
    assert sanitize_slide_image_filename(filename) == expected


def test_resolve_confined_slide_image_returns_existing_file(tmp_path: Path) -> None:
    image = tmp_path / "slide-1.jpg"
    image.write_bytes(b"fake")

    resolved = resolve_confined_slide_image(tmp_path, "slide-1.jpg")

    assert resolved == image.resolve()


def test_resolve_confined_slide_image_rejects_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.jpg"
    outside.write_bytes(b"fake")

    resolved = resolve_confined_slide_image(tmp_path, "../outside.jpg")

    assert resolved is None


def test_resolve_confined_slide_image_falls_back_to_jpg_extension(
    tmp_path: Path,
) -> None:
    image = tmp_path / "slide-3.jpg"
    image.write_bytes(b"fake")

    resolved = resolve_confined_slide_image(tmp_path, "slide-3")

    assert resolved == image.resolve()
