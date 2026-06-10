"""Repair stale or missing current.json artifact index files."""

from __future__ import annotations

import json
from pathlib import Path

from rag_backend.application.services.carousel.artifact_build_support import (
    write_current_index,
)
from rag_backend.domain.constants.artifact_build import ARTIFACT_CURRENT_INDEX_FILENAME
from rag_backend.domain.models import CarouselProject


def reconcile_current_index(project: CarouselProject) -> bool:
    """Ensure current.json matches the database artifact version when versioned."""
    if not project.output_dir or not project.artifact_version:
        return False
    project_root = Path(project.output_dir).resolve()
    if not project_root.is_dir():
        return False
    index_path = project_root / ARTIFACT_CURRENT_INDEX_FILENAME
    if index_path.is_file():
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        stored_version = payload.get("artifact_version")
        if stored_version == project.artifact_version:
            return False
    write_current_index(project_root, project.artifact_version)
    return True


__all__ = ["reconcile_current_index"]
