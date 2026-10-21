"""The gate repair's source, patch and service edges.

The happy paths run on the real engine in
tests/unit/application/test_content_quality_gate_flow_ae0392.py; these cover
the guards (no checkpoint, no copy, nothing to change, lost CAS).

Gherkin: tests/features/autopilot_content_quality_gate_ae0392.feature
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.owner_autofix_gate import (
    GatePatchInput,
    blocking_rules,
    gate_patch,
)
from rag_backend.application.services.carousel.owner_autofix_service import (
    AutofixApplyCommand,
    OwnerAutofixDeps,
    OwnerAutofixService,
)
from rag_backend.application.services.carousel.owner_autofix_source import (
    AutofixSourceRequest,
    load_gate_source,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_NOTHING_TO_FIX,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.protocols.repositories import CarouselRepository
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from tests.unit.application.content_gate_fixtures_ae0392 import (
    GateSeed,
    emoji_body_3,
    lowercase_heading_5,
    seed_gate,
)
from tests.unit.application.owner_autofix_fixtures_ae0367 import (
    LOCK_VERSION,
    V3,
    FakeChatModel,
    build_engine,
)

_ID = "22222222-2222-2222-2222-222222222222"


@dataclass
class _Project:
    id: UUID
    topic: str = "Argon"
    presentation_policy_version: str | None = None


@dataclass
class _Repo:
    project: _Project | None

    async def get_project_by_id(self, project_id: UUID) -> _Project | None:
        del project_id
        return self.project


@dataclass
class _Workflow:
    state: Mapping[str, object] | None

    async def get_workflow_state(self, project_id: str) -> Mapping[str, object] | None:
        del project_id
        return self.state

    async def update_workflow_state(
        self, project_id: str, values: dict[str, object]
    ) -> None:
        del project_id, values


def _request(
    project: _Project | None, state: Mapping[str, object] | None
) -> AutofixSourceRequest:
    return AutofixSourceRequest(
        repo=cast(CarouselRepository, _Repo(project=project)),
        project_id=_ID,
        workflow=_Workflow(state=state),
    )


_SLIDES = {"localized_slides": [{"slide_index": 1, "presentation_pt": {}}]}


@pytest.mark.unit
@pytest.mark.asyncio
class TestLoadGateSource:
    async def test_needs_a_workflow_a_project_a_state_and_copy(self) -> None:
        project = _Project(id=UUID(_ID))
        no_workflow = AutofixSourceRequest(
            repo=cast(CarouselRepository, _Repo(project=project)), project_id=_ID
        )
        assert await load_gate_source(no_workflow) is None
        assert await load_gate_source(_request(None, _SLIDES)) is None
        assert await load_gate_source(_request(project, None)) is None
        assert await load_gate_source(_request(project, {})) is None
        empty = {"localized_slides": "x"}
        assert await load_gate_source(_request(project, empty)) is None

    async def test_policy_version_prefers_the_checkpoint(self) -> None:
        project = _Project(id=UUID(_ID))
        source = await load_gate_source(_request(project, _SLIDES))
        assert source is not None
        assert source.policy_version == DEFAULT_PRESENTATION_POLICY_VERSION
        stamped = {**_SLIDES, "presentation_policy_version": V3}
        source = await load_gate_source(_request(project, stamped))
        assert source is not None and source.policy_version == V3


class TestGatePatch:
    def test_unchanged_copy_is_no_patch(self) -> None:
        records = [{"slide_index": 1}]
        patch = gate_patch(GatePatchInput(state={}, before=records, after=records))
        assert patch is None

    def test_blocking_rules_skip_warnings_and_junk(self) -> None:
        report = {
            "violations": [
                {"code": "a"},
                {"code": "a", "severity": "blocker"},
                {"code": "b", "severity": "warning"},
                {"code": ""},
                "junk",
            ]
        }
        assert blocking_rules(report) == ("a",)
        assert blocking_rules({"violations": "x"}) == ()
        assert blocking_rules(None) == ()


def _service(db: AsyncSession, engine: object) -> OwnerAutofixService:
    return OwnerAutofixService(
        OwnerAutofixDeps(
            db=db,
            repo=PostgresCarouselRepository(session=db),
            workflow=cast(_Workflow, engine),
        )
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestRepairGateService:
    async def test_nothing_to_fix_reports_the_rules_left(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: A violation the repair cannot fix gets a targeted revise."""
        engine = build_engine(FakeChatModel())
        project_id = await seed_gate(
            engine, db_session, GateSeed(breaks=(emoji_body_3,))
        )
        result = await _service(db_session, engine).repair_gate(
            AutofixApplyCommand(project_id=project_id, expected_version=LOCK_VERSION)
        )
        assert result.status == AUTOFIX_STATUS_NOTHING_TO_FIX
        assert result.remaining_rules == ("visible_emoji_forbidden",)

    async def test_lost_cas_is_a_conflict(self, db_session: AsyncSession) -> None:
        """Scenario: Another writer holds the carousel during the repair."""
        engine = build_engine(FakeChatModel())
        seed = GateSeed(breaks=(lowercase_heading_5,))
        project_id = await seed_gate(engine, db_session, seed)
        result = await _service(db_session, engine).repair_gate(
            AutofixApplyCommand(
                project_id=project_id, expected_version=LOCK_VERSION - 1
            )
        )
        assert result.status == AUTOFIX_STATUS_CONFLICT

    async def test_missing_carousel_is_nothing_to_fix(
        self, db_session: AsyncSession
    ) -> None:
        engine = build_engine(FakeChatModel())
        result = await _service(db_session, engine).repair_gate(
            AutofixApplyCommand(project_id=_ID, expected_version=1)
        )
        assert result.status == AUTOFIX_STATUS_NOTHING_TO_FIX
