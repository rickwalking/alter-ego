"""Unit tests for current.json artifact index reconciliation."""

from __future__ import annotations

import json
from pathlib import Path

from rag_backend.application.services.carousel.artifact_index_reconciler import (
    reconcile_current_index,
)
from rag_backend.domain.constants.artifact_build import ARTIFACT_CURRENT_INDEX_FILENAME
from rag_backend.domain.models import CarouselProject


def _project(tmp_path: Path, *, artifact_version: str | None) -> CarouselProject:
    return CarouselProject(
        topic="Topic",
        audience="Audience",
        niche="Niche",
        title="Test",
        output_dir=str(tmp_path),
        artifact_version=artifact_version,
    )


def test_reconcile_current_index_writes_missing_index(tmp_path: Path) -> None:
    project = _project(tmp_path, artifact_version="v2")

    changed = reconcile_current_index(project)

    assert changed is True
    payload = json.loads(
        (tmp_path / ARTIFACT_CURRENT_INDEX_FILENAME).read_text(encoding="utf-8")
    )
    assert payload["artifact_version"] == "v2"


def test_reconcile_current_index_updates_stale_version(tmp_path: Path) -> None:
    index_path = tmp_path / ARTIFACT_CURRENT_INDEX_FILENAME
    index_path.write_text(
        json.dumps({"artifact_version": "v1"}),
        encoding="utf-8",
    )
    project = _project(tmp_path, artifact_version="v2")

    changed = reconcile_current_index(project)

    assert changed is True
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert payload["artifact_version"] == "v2"


def test_reconcile_current_index_skips_missing_output_dir(tmp_path: Path) -> None:
    missing_dir = tmp_path / "missing"
    project = _project(missing_dir, artifact_version="v2")

    changed = reconcile_current_index(project)

    assert changed is False


def test_reconcile_current_index_noop_when_current(tmp_path: Path) -> None:
    index_path = tmp_path / ARTIFACT_CURRENT_INDEX_FILENAME
    index_path.write_text(
        json.dumps({"artifact_version": "v2"}),
        encoding="utf-8",
    )
    project = _project(tmp_path, artifact_version="v2")

    changed = reconcile_current_index(project)

    assert changed is False
