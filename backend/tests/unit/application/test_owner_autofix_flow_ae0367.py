"""The "Fix issues" flow end to end on the real editorial engine.

Real: the SQLite slide rows, ``EditorialWorkflowService`` with a LangGraph
checkpoint, the editorial facade, the owner autofix service, the autopilot
webhook use case, runner and review facts. Fake: the chat model (EN
re-translate) and the renderer (republish).

Gherkin: tests/features/autopilot_owner_autofix.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import cast

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel import carousel_republish
from rag_backend.application.services.carousel.editorial_finalize import (
    CarouselFinalizeResult,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.owner_autofix_service import (
    AutofixApplyCommand,
    OwnerAutofixDeps,
    OwnerAutofixService,
)
from rag_backend.application.services.carousel.presentation_casing_markers import (
    CASING_REPAIRS_KEY,
)
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.application.owner_actions import (
    OwnerActionDeps,
    OwnerActionService,
)
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.domain.autofix import (
    AutofixCommand,
    AutofixStatus,
    ContentAutofixer,
)
from rag_backend.modules.autopilot.domain.gate import GateSnapshot
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.content_autofixer import (
    AutofixerConfig,
    InProcessContentAutofixer,
)
from rag_backend.modules.autopilot.infrastructure.review_facts import (
    CarouselReviewFacts,
)
from rag_backend.modules.autopilot.webhook_constants import (
    ANSWER_ALREADY,
    ANSWER_FIXING,
    ANSWER_NOTHING_TO_FIX,
    TEXT_SUPERSEDED,
)
from tests.unit.application.owner_autofix_fixtures_ae0367 import (
    BROKEN_HEADING_5,
    FIXED_BODY_3,
    FIXED_HEADING_5,
    IMAGE_PATH,
    LOCK_VERSION,
    PT_BODY_6,
    FakeChatModel,
    break_carousel,
    build_engine,
    row,
    seed_carousel,
    seed_checkpoint,
)
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_owner_actions import (
    _OWNER,
    _STRANGER,
    _Claims,
    _Editorial,
    _Messenger,
    _Notices,
    _Pending,
    _Release,
    _Runs,
    _snapshot,
    _tap,
    _Topics,
    _world,
)


@dataclass
class _Renders:
    calls: list[str] = field(default_factory=list)

    async def __call__(
        self, db: AsyncSession, project_id: str
    ) -> CarouselFinalizeResult:
        del db
        self.calls.append(project_id)
        return CarouselFinalizeResult(completed=True, errors=())


@dataclass
class _Gate(_Editorial):
    """Final review at the row's current lock version (the real driver's value)."""

    db: AsyncSession | None = None
    project_id: str = ""

    async def read_gate(self, project_id: str) -> GateSnapshot:
        assert self.db is not None
        version = await self.db.scalar(
            select(CarouselProjectModel.lock_version).where(
                CarouselProjectModel.id == project_id
            )
        )
        return replace(_snapshot(), lock_version=int(version or 1))


@dataclass
class _Flow:
    db: AsyncSession
    project_id: str
    llm: FakeChatModel
    engine: EditorialWorkflowService
    renders: _Renders
    runs: _Runs
    recovery: _Recovery
    messenger: _Messenger
    service: OwnerActionService
    autofixer: InProcessContentAutofixer


async def _flow(
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    *,
    broken: bool = True,
    llm: FakeChatModel | None = None,
) -> _Flow:
    project_id = await seed_carousel(db)
    if broken:
        await break_carousel(db, project_id)
    model = llm or FakeChatModel()
    engine = build_engine(model)
    await seed_checkpoint(engine, db, project_id)
    renders = _Renders()
    monkeypatch.setattr(carousel_republish, "republish_completed_carousel", renders)
    base = _world()
    runs = _Runs(run=replace(base.runs.run, carousel_project_id=project_id))
    recovery = _Recovery(runs=runs)
    messenger = _Messenger()
    autofixer = InProcessContentAutofixer(
        AutofixerConfig(session=db, engine_factory=lambda: engine)
    )
    service = OwnerActionService(
        OwnerActionDeps(
            runs=runs,
            updates=_Claims(),
            pending=_Pending(),
            editorial=_Editorial(),
            release=_Release(),
            messenger=messenger,
            recovery=recovery,
            clock=_Clock(),
            owner_chat_id=_OWNER,
            autofix=autofixer,
        )
    )
    return _Flow(
        db=db,
        project_id=project_id,
        llm=model,
        engine=engine,
        renders=renders,
        runs=runs,
        recovery=recovery,
        messenger=messenger,
        service=service,
        autofixer=autofixer,
    )


class _Clock:
    def now(self) -> object:
        from datetime import UTC, datetime

        return datetime(2026, 10, 14, tzinfo=UTC)


async def _tap_fix(flow: _Flow, update_id: int, actor: str = _OWNER) -> None:
    await flow.service.handle(
        _tap(update_id, f"ap:fix:{flow.runs.run.run_id}", actor=actor)
    )
    await flow.service.deliver()


async def _tick(flow: _Flow) -> _Notices:
    notices = _Notices()
    runner = AutopilotRunner(
        RunnerDependencies(
            runs=flow.runs,
            topics=_Topics(),
            editorial=_Gate(db=flow.db, project_id=flow.project_id),
            notices=notices,
            recovery=flow.recovery,
            owner_user_id="owner",
            inputs=FakeProjectInputs(),
            autofix=flow.autofixer,
        )
    )
    await runner.tick()
    return notices


async def _review_lines(flow: _Flow) -> tuple[tuple[str, ...], bool]:
    facts = await CarouselReviewFacts(flow.db, flow.autofixer).load(flow.project_id)
    assert facts is not None
    return facts.issues, facts.fixable


def _extras(slide: object) -> dict[str, object]:
    return dict(cast(dict[str, object], getattr(slide, "extras", None) or {}))


@pytest.mark.unit
@pytest.mark.asyncio
class TestOwnerAutofixFlow:
    """Scenarios of autopilot_owner_autofix.feature on the real engine."""

    async def test_review_lists_the_issues_and_offers_the_fix(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: The review message lists the issues and offers the fix."""
        flow = await _flow(db_session, monkeypatch)
        lines, fixable = await _review_lines(flow)
        assert fixable
        assert "Slide 4: no body or features" in lines
        assert "Slide 3: broken bold markup" in lines
        assert len(lines) == 5

    async def test_happy_path_tap_then_tick(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Happy path: the owner taps Fix issues."""
        flow = await _flow(db_session, monkeypatch)

        await _tap_fix(flow, 1)

        assert flow.runs.run.state is AutopilotRunState.REWORKING
        assert flow.messenger.edits[-1].text == TEXT_SUPERSEDED
        assert flow.messenger.answers[-1].text == ANSWER_FIXING
        assert (await row(db_session, flow.project_id, 5)).heading == BROKEN_HEADING_5
        assert flow.llm.calls == 0 and flow.renders.calls == []

        notices = await _tick(flow)

        slide3 = await row(db_session, flow.project_id, 3)
        slide4 = await row(db_session, flow.project_id, 4)
        slide5 = await row(db_session, flow.project_id, 5)
        slide6 = await row(db_session, flow.project_id, 6)
        assert slide3.body == FIXED_BODY_3
        assert slide5.heading == FIXED_HEADING_5
        features = cast(list[dict[str, str]], _extras(slide4)["features"])
        assert [item["title"] for item in features] == [
            "Simulação Real2Sim",
            "Braços robóticos",
            "Parada segura",
        ]
        assert {item["icon_name"] for item in features} <= {
            "chart-column",
            "book-open",
            "newspaper",
        }
        en4 = cast(dict[str, object], _extras(slide4)["translation_en"])
        en_features = cast(list[dict[str, str]], en4["features"])
        assert en_features[0]["title"] == "English copy 4:features[0].title"
        en6 = cast(dict[str, object], _extras(slide6)["translation_en"])
        assert en6["body"] == "English copy 6:body"
        assert slide5.image_path == IMAGE_PATH.format(n=5)
        assert _extras(slide5)["image_prompt"] == "Editorial illustration 5"
        assert flow.llm.calls == 1
        assert flow.renders.calls == [flow.project_id]
        assert flow.runs.run.state is AutopilotRunState.AWAITING_OWNER
        assert [notice.revision for notice in notices.ready] == [LOCK_VERSION + 1]

        state = await flow.engine.get_workflow_state(flow.project_id)
        assert state is not None
        localized = cast(list[dict[str, object]], state["localized_slides"])
        pt5 = cast(dict[str, object], localized[4]["presentation_pt"])
        assert pt5["heading"] == FIXED_HEADING_5
        assert CASING_REPAIRS_KEY not in localized[4]

        lines, fixable = await _review_lines(flow)
        assert not fixable
        assert not any("Slide 5" in line or "Slide 4" in line for line in lines)

    async def test_double_tap_fixes_once(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Double tap fixes once."""
        flow = await _flow(db_session, monkeypatch)
        await _tap_fix(flow, 1)
        await _tap_fix(flow, 2)
        await _tap_fix(flow, 2)
        await _tick(flow)
        await _tick(flow)
        answers = [answer.text for answer in flow.messenger.answers]
        assert answers == [ANSWER_FIXING, ANSWER_ALREADY]
        assert flow.renders.calls == [flow.project_id]
        assert flow.llm.calls == 1

    async def test_nothing_to_fix(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Nothing to fix (and: a clean carousel offers no button)."""
        flow = await _flow(db_session, monkeypatch, broken=False)
        lines, fixable = await _review_lines(flow)
        assert (lines, fixable) == ((), False)
        await _tap_fix(flow, 1)
        assert [answer.text for answer in flow.messenger.answers] == [
            ANSWER_NOTHING_TO_FIX
        ]
        assert flow.runs.run.state is AutopilotRunState.AWAITING_OWNER
        assert flow.runs.run.rework_phase is None
        assert flow.renders.calls == []

    async def test_partial_fix_keeps_the_rework_issue(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Partial fix: issues that need a rework remain."""
        project_id = await seed_carousel(db_session)
        slide3 = await row(db_session, project_id, 3)
        slide3.body = "O Argon é rápido. " * 20
        await PostgresCarouselRepository(session=db_session).update_slide(slide3)
        flow = await _flow_for(db_session, monkeypatch, project_id)
        slide5 = await row(db_session, project_id, 5)
        slide5.heading = BROKEN_HEADING_5
        await PostgresCarouselRepository(session=db_session).update_slide(slide5)

        await _tap_fix(flow, 1)
        await _tick(flow)

        assert (await row(db_session, project_id, 5)).heading == FIXED_HEADING_5
        lines, _ = await _review_lines(flow)
        assert "Slide 3: body too long" in lines

    async def test_stranger_tap_is_ignored(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: A non-owner tap is ignored."""
        flow = await _flow(db_session, monkeypatch)
        await _tap_fix(flow, 1, actor=_STRANGER)
        assert flow.runs.run.state is AutopilotRunState.AWAITING_OWNER
        assert flow.messenger.answers == [] and flow.messenger.edits == []
        assert flow.runs.run.rework_phase is None

    async def test_translation_failure_keeps_the_en_copy(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: EN re-translation fails."""
        flow = await _flow(db_session, monkeypatch, llm=FakeChatModel(fail=True))
        await _tap_fix(flow, 1)
        await _tick(flow)
        assert flow.llm.calls == 2
        slide6 = await row(db_session, flow.project_id, 6)
        en6 = cast(dict[str, object], _extras(slide6)["translation_en"])
        assert en6["body"] == PT_BODY_6
        assert (await row(db_session, flow.project_id, 5)).heading == FIXED_HEADING_5
        assert flow.runs.run.state is AutopilotRunState.AWAITING_OWNER
        lines, fixable = await _review_lines(flow)
        assert "Slide 6 EN: not translated" in lines
        assert fixable


async def _flow_for(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch, project_id: str
) -> _Flow:
    """A flow over an already seeded carousel."""
    flow = await _flow(db, monkeypatch, broken=False)
    engine = build_engine(flow.llm)
    await seed_checkpoint(engine, db, project_id)
    autofixer = InProcessContentAutofixer(
        AutofixerConfig(session=db, engine_factory=lambda: engine)
    )
    runs = _Runs(run=replace(flow.runs.run, carousel_project_id=project_id))
    recovery = _Recovery(runs=runs)
    service = OwnerActionService(
        replace(
            flow.service._deps,
            runs=runs,
            recovery=recovery,
            autofix=autofixer,
        )
    )
    return replace(
        flow,
        project_id=project_id,
        engine=engine,
        runs=runs,
        recovery=recovery,
        service=service,
        autofixer=autofixer,
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestOwnerAutofixServiceEdges:
    """Lock-version CAS, lock conflict, render errors, missing carousel."""

    async def test_a_stale_version_is_a_conflict_and_writes_nothing(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        flow = await _flow(db_session, monkeypatch)
        outcome = await flow.autofixer.autofix(
            AutofixCommand(
                project_id=flow.project_id, expected_version=LOCK_VERSION - 1
            )
        )
        assert outcome.status is AutofixStatus.CONFLICT
        assert (await row(db_session, flow.project_id, 5)).heading == BROKEN_HEADING_5
        assert flow.renders.calls == []

    async def test_a_held_lock_is_a_conflict(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        flow = await _flow(db_session, monkeypatch)

        async def _held(*args: object, **kwargs: object) -> None:
            raise CarouselConflictError(
                CarouselConflict.for_code("mutation_in_progress")
            )

        from rag_backend.application.services.carousel import owner_autofix_lock

        monkeypatch.setattr(
            owner_autofix_lock.CarouselProjectWriteOwner,
            "bump_resume_lock_version",
            _held,
        )
        outcome = await flow.autofixer.autofix(
            AutofixCommand(project_id=flow.project_id, expected_version=LOCK_VERSION)
        )
        assert outcome.status is AutofixStatus.CONFLICT

    async def test_render_errors_are_reported_as_an_issue(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        flow = await _flow(db_session, monkeypatch)

        async def _broken(db: AsyncSession, project_id: str) -> CarouselFinalizeResult:
            del db, project_id
            return CarouselFinalizeResult(completed=False, errors=("export failed",))

        monkeypatch.setattr(carousel_republish, "republish_completed_carousel", _broken)
        outcome = await flow.autofixer.autofix(
            AutofixCommand(project_id=flow.project_id, expected_version=LOCK_VERSION)
        )
        assert outcome.status is AutofixStatus.FIXED
        assert outcome.remaining[0] == "Carousel: re-render failed (export failed)"

    async def test_a_republish_conflict_becomes_a_render_error(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        flow = await _flow(db_session, monkeypatch)

        async def _busy(db: AsyncSession, project_id: str) -> CarouselFinalizeResult:
            raise CarouselConflictError(CarouselConflict.for_code("build_in_progress"))

        monkeypatch.setattr(carousel_republish, "republish_completed_carousel", _busy)
        outcome = await flow.autofixer.autofix(
            AutofixCommand(project_id=flow.project_id, expected_version=LOCK_VERSION)
        )
        assert outcome.remaining[0] == "Carousel: re-render failed (build_in_progress)"

    async def test_missing_carousel_and_rows_only_inspection(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without the engine the inspection sees rows only: no outline key points and
        no EN translation.
        """
        flow = await _flow(db_session, monkeypatch)
        service = OwnerAutofixService(
            OwnerAutofixDeps(db=db_session, repo=PostgresCarouselRepository(db_session))
        )
        missing = "00000000-0000-4000-8000-000000000000"
        assert (await service.inspect(missing)).lines == ()
        result = await service.apply(
            AutofixApplyCommand(project_id=missing, expected_version=1)
        )
        assert result.status == "nothing_to_fix"
        found = await service.inspect(flow.project_id)
        assert found.fixable
        applied = await service.apply(
            AutofixApplyCommand(
                project_id=flow.project_id, expected_version=LOCK_VERSION
            )
        )
        assert applied.translation_failed
        assert flow.renders.calls == []

    async def test_review_facts_survive_a_failing_inspection(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        flow = await _flow(db_session, monkeypatch)

        class _Broken:
            async def inspect(self, project_id: str) -> object:
                raise RuntimeError(project_id)

        broken = cast(ContentAutofixer, _Broken())
        facts = await CarouselReviewFacts(db_session, broken).load(flow.project_id)
        assert facts is not None and facts.issues == () and not facts.fixable
        assert (
            await CarouselReviewFacts(db_session).load(
                "00000000-0000-4000-8000-000000000000"
            )
            is None
        )


@pytest.mark.unit
@pytest.mark.asyncio
class TestOwnerAutofixWorkerRace:
    """The webhook saw something fixable, the worker finds nothing left."""

    async def test_nothing_left_still_moves_the_review_revision(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        flow = await _flow(db_session, monkeypatch, broken=False)
        outcome = await flow.autofixer.autofix(
            AutofixCommand(project_id=flow.project_id, expected_version=LOCK_VERSION)
        )
        assert outcome.status is AutofixStatus.NOTHING_TO_FIX
        version = await db_session.scalar(
            select(CarouselProjectModel.lock_version).where(
                CarouselProjectModel.id == flow.project_id
            )
        )
        assert version == LOCK_VERSION + 1
        assert flow.renders.calls == []

    async def test_other_cas_errors_propagate(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        flow = await _flow(db_session, monkeypatch)

        async def _broken(*args: object, **kwargs: object) -> None:
            raise ValueError("project row missing")

        from rag_backend.application.services.carousel import owner_autofix_lock

        monkeypatch.setattr(
            owner_autofix_lock.CarouselProjectWriteOwner,
            "bump_resume_lock_version",
            _broken,
        )
        with pytest.raises(ValueError, match="project row missing"):
            await flow.autofixer.autofix(
                AutofixCommand(
                    project_id=flow.project_id, expected_version=LOCK_VERSION
                )
            )

    async def test_a_failing_export_becomes_a_render_error(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        flow = await _flow(db_session, monkeypatch)

        async def _disk(db: AsyncSession, project_id: str) -> CarouselFinalizeResult:
            raise OSError("disk full")

        monkeypatch.setattr(carousel_republish, "republish_completed_carousel", _disk)
        outcome = await flow.autofixer.autofix(
            AutofixCommand(project_id=flow.project_id, expected_version=LOCK_VERSION)
        )
        assert outcome.remaining[0] == "Carousel: re-render failed (disk full)"

    async def test_review_facts_without_an_autofixer_list_nothing(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        flow = await _flow(db_session, monkeypatch)
        facts = await CarouselReviewFacts(db_session).load(flow.project_id)
        assert facts is not None and facts.issues == () and not facts.fixable


def test_the_lock_uses_the_session_engine() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    from rag_backend.application.services.carousel.owner_autofix_lock import (
        lock_engine,
    )

    engine = create_async_engine("sqlite+aiosqlite://")
    assert lock_engine(AsyncSession(bind=engine)) is engine
