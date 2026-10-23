"""Rows of the Knowledge Base carousel-sources listing."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from rag_backend.api.dependencies.carousel_access import _to_item
from rag_backend.infrastructure.database.models.source_comment import (
    ContentSourceModel,
)


def _source(source_type: str, content: str) -> ContentSourceModel:
    return ContentSourceModel(
        id=str(uuid4()),
        project_id=str(uuid4()),
        source_type=source_type,
        title="Fonte",
        content=content,
        created_by="seed",
        created_at=datetime(2026, 10, 1, tzinfo=UTC),
    )


def test_url_source_carries_its_trimmed_url() -> None:
    """Scenario: My carousels' sources are listed newest first with their carousel"""
    item = _to_item(_source("url", "  https://example.org/a  "), "IA")

    assert item.url == "https://example.org/a"
    assert item.project_title == "IA"


def test_url_source_without_a_link_carries_no_url() -> None:
    """Scenario: My carousels' sources are listed newest first with their carousel"""
    item = _to_item(_source("url", "see the attached notes"), None)

    assert item.url is None
    assert item.project_title == ""


def test_other_source_types_carry_no_url() -> None:
    """Scenario: My carousels' sources are listed newest first with their carousel"""
    assert _to_item(_source("note", "https://example.org/a"), "IA").url is None
