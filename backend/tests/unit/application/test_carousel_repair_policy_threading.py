"""Policy-version threading into content validation (AE-0311 deliverable 3).

A v2-stamped project must fire the AE-0312 casing rules live at the content
gate; a legacy NULL/v1 project keeps v1 semantics. This absorbed the gap left
open by AE-0312 (the stamped column was never threaded into workflow state or
the content-phase validation command).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    _state_policy_version,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

_V1 = PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
_V2 = PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2


def _factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_rows(test_engine: AsyncEngine) -> AsyncIterator[None]:
    """The session-scoped SQLite engine commits for real; purge our rows."""
    yield
    async with _factory(test_engine)() as db:
        await db.execute(delete(CarouselProjectModel))
        await db.commit()


async def _add_project(db: AsyncSession, policy_version: str | None) -> str:
    project = CarouselProjectModel(
        id=str(uuid.uuid4()),
        topic="Policy",
        audience="Devs",
        niche="Tech",
        status="in_review",
        current_phase="brief",
        phase_status="pending",
        lock_version=1,
        presentation_policy_version=policy_version,
    )
    db.add(project)
    await db.commit()
    return str(project.id)


def _lowercase_proper_noun_slide() -> list[dict[str, object]]:
    return [
        {
            "slide_index": 2,
            "slide_type": "content",
            "presentation_pt": {
                "slide_type": "content",
                "heading": "como o claude muda tudo",
                "body": "Um corpo limpo e curto de exemplo.",
            },
            "presentation_en": {
                "slide_type": "content",
                "heading": "How Claude Changes Everything",
                "body": "A short clean body sample.",
            },
        }
    ]


class TestResolvePolicyVersion:
    """The stamped column is read into workflow-state seeding."""

    @pytest.mark.asyncio
    async def test_v2_column_is_resolved(self, test_engine: AsyncEngine) -> None:
        async with _factory(test_engine)() as db:
            pid = await _add_project(db, _V2)
            resolved = (
                await EditorialWorkflowService._resolve_presentation_policy_version(
                    db, pid
                )
            )
            assert resolved == _V2

    @pytest.mark.asyncio
    async def test_null_column_falls_back_to_none(
        self, test_engine: AsyncEngine
    ) -> None:
        async with _factory(test_engine)() as db:
            pid = await _add_project(db, None)
            resolved = (
                await EditorialWorkflowService._resolve_presentation_policy_version(
                    db, pid
                )
            )
            assert resolved is None


class TestStatePolicyThreading:
    """The seeded state version reaches the content-phase validation command."""

    def test_state_policy_version_reads_seeded_value(self) -> None:
        assert _state_policy_version({"presentation_policy_version": _V2}) == _V2
        assert _state_policy_version({"presentation_policy_version": " "}) is None
        assert _state_policy_version({}) is None


class TestContentGateSemantics:
    """Threaded v2 fires casing rules live; v1 keeps its semantics."""

    def test_v2_flags_casing_warnings_at_content_gate(self) -> None:
        report = validate_localized_slides(
            _lowercase_proper_noun_slide(), policy_version=_V2
        )
        codes = {violation.code for violation in report.violations}
        assert "proper_noun_casing" in codes
        assert "heading_not_sentence_case_pt" in codes

    def test_v1_keeps_semantics_without_casing_rules(self) -> None:
        report = validate_localized_slides(
            _lowercase_proper_noun_slide(), policy_version=_V1
        )
        assert report.violations == []
