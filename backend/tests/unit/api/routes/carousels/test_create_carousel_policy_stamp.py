"""Create-time presentation-policy stamping tests (AE-0312).

Gherkin: tests/features/carousel_pt_casing_severity.feature
"""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.routes.carousels.crud import create_carousel
from rag_backend.api.schemas.carousel import CarouselProjectCreate
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_HEADING_NOT_SENTENCE_CASE_PT,
)
from rag_backend.domain.constants.presentation_policy import (
    CREATE_TIME_PRESENTATION_POLICY_VERSION,
    DEFAULT_PRESENTATION_POLICY_VERSION,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
)
from rag_backend.domain.models import CarouselProject, User
from rag_backend.domain.protocols import CarouselRepository


class _CaptureRepo:
    """Captures the CarouselProject passed to create_project."""

    def __init__(self) -> None:
        self.captured: CarouselProject | None = None

    async def create_project(self, project: CarouselProject) -> CarouselProject:
        self.captured = project
        project.id = uuid4()
        return project


class _NoopSession:
    async def get(self, model: object, key: object) -> None:
        return None

    async def commit(self) -> None:
        return None


@pytest.mark.unit
class TestCreateTimeStamping:
    """New carousels are stamped v2; legacy NULL rows keep v1 semantics."""

    def test_create_time_constant_is_v2(self) -> None:
        assert CREATE_TIME_PRESENTATION_POLICY_VERSION == (
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2
        )
        assert DEFAULT_PRESENTATION_POLICY_VERSION == "hero_lower_third_v1"

    async def test_create_carousel_stamps_v2(self) -> None:
        repo = _CaptureRepo()
        user = User(
            email="e@x.com",
            full_name="Editor",
            hashed_password="x",
            id=uuid4(),
        )
        request = CarouselProjectCreate(
            topic="AI", audience="devs", niche="AI Education"
        )

        await create_carousel(
            request,
            user,
            cast(CarouselRepository, repo),
            cast(AsyncSession, _NoopSession()),
        )

        assert repo.captured is not None
        assert repo.captured.presentation_policy_version == (
            CREATE_TIME_PRESENTATION_POLICY_VERSION
        )

    def test_legacy_null_version_keeps_v1_semantics(self) -> None:
        """A legacy NULL-version row (policy_version=None) validates under v1."""
        slide = {
            "slide_index": 1,
            "slide_type": "intro",
            "presentation_pt": {
                "slide_type": "intro",
                "heading": "um título minúsculo no claude",
                "body": "corpo minúsculo.",
            },
            "presentation_en": {
                "slide_type": "intro",
                "heading": "Valid heading",
                "body": "Valid body.",
            },
        }

        report = validate_localized_slides([slide], policy_version=None)

        codes = {violation.code for violation in report.violations}
        assert VIOLATION_HEADING_NOT_SENTENCE_CASE_PT not in codes
