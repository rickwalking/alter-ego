"""A failed background resume stores a safe cause on the row and the event.

Feature: phase_failure_cause_ae0600.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, nullcontext
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, ValidationError

from rag_backend.application.services.carousel.editorial_distribution_blog import (
    ERR_TRANSLATIONS_REQUIRED,
)
from rag_backend.application.services.carousel.editorial_distribution_constants import (
    ERR_EN_TRANSLATION_PARSE_FAILED,
)
from rag_backend.application.services.carousel.editorial_workflow_resume_failures import (
    MarkFailedParams,
)
from rag_backend.application.services.carousel.editorial_workflow_resume_runner import (
    BackgroundResumeParams,
    _mark_background_resume_failed,
    execute_resume_run,
)
from rag_backend.application.services.carousel.workflow_failure_cause import (
    failure_cause,
    failure_cause_code,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.artifact_build import (
    ERR_ARTIFACT_STAGING_INCOMPLETE,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_FAILED,
    ERR_PERSONA_SCORE_TOO_LOW,
    PHASE_OUTLINE,
    PHASE_STATUS_FAILED,
    REVIEW_ACTION_APPROVE,
)
from rag_backend.domain.constants.workflow_failure import (
    CAUSE_ARTIFACT_STAGING_INCOMPLETE,
    CAUSE_INVALID_JSON,
    CAUSE_TRANSLATIONS_REQUIRED,
    CAUSE_UNCLASSIFIED,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.generation_queue.events_public import (
    OUTCOME_FAILED,
    WorkflowOutcomeObservation,
)

_RUNNER = "rag_backend.application.services.carousel.editorial_workflow_resume_runner"
_HEARTBEAT = (
    "rag_backend.application.services.carousel.editorial_workflow_run_heartbeat"
)
_FAILURES = (
    "rag_backend.application.services.carousel.editorial_workflow_resume_failures"
)
_PROJECT_ID = "project-ae0600"
_FREE_TEXT = "topic about Pedro's secret plan"
_CAUSE_TRANSLATION = f"ValueError: {ERR_EN_TRANSLATION_PARSE_FAILED}"


@pytest.fixture(autouse=True)
def _hermetic_run_seams() -> Iterator[None]:
    """The fence, trace scope, heartbeat and stage beats open their own sessions."""
    with (
        patch(f"{_RUNNER}.read_run_fence", new=AsyncMock(return_value=None)),
        patch(
            f"{_RUNNER}.open_run_trace_scope",
            new=AsyncMock(side_effect=lambda *_: nullcontext()),
        ),
        patch(f"{_HEARTBEAT}.write_run_heartbeat_with_retry", new=AsyncMock()),
        patch(f"{_RUNNER}.write_run_heartbeat_once", new=AsyncMock()),
        patch(f"{_RUNNER}.publish_run_stage_changed", new=AsyncMock()),
        patch(
            f"{_RUNNER}.resume_persona.load_project_persona",
            new=AsyncMock(return_value=None),
        ),
    ):
        yield


def _params() -> BackgroundResumeParams:
    return BackgroundResumeParams(
        project_id=_PROJECT_ID,
        action=REVIEW_ACTION_APPROVE,
        reviewer_id="reviewer-1",
        feedback=None,
        project_title="Carousel",
        structured_feedback=None,
    )


def _session_factory(db: AsyncMock) -> MagicMock:
    @asynccontextmanager
    async def session() -> AsyncIterator[AsyncMock]:
        yield db

    return MagicMock(side_effect=lambda: session())


class _Strict(BaseModel):
    count: int


def _validation_error() -> ValidationError:
    try:
        _Strict.model_validate({"count": _FREE_TEXT})
    except ValidationError as exc:
        return exc
    raise AssertionError


@pytest.mark.unit
class TestFailureCauseCode:
    @pytest.mark.parametrize(
        ("message", "code"),
        [
            (ERR_EN_TRANSLATION_PARSE_FAILED, ERR_EN_TRANSLATION_PARSE_FAILED),
            (ERR_PERSONA_SCORE_TOO_LOW, ERR_PERSONA_SCORE_TOO_LOW),
            (ERR_INVALID_JSON, CAUSE_INVALID_JSON),
            (ERR_ARTIFACT_STAGING_INCOMPLETE, CAUSE_ARTIFACT_STAGING_INCOMPLETE),
            (ERR_TRANSLATIONS_REQUIRED, CAUSE_TRANSLATIONS_REQUIRED),
            (_FREE_TEXT, CAUSE_UNCLASSIFIED),
            ("", CAUSE_UNCLASSIFIED),
            ("boom", CAUSE_UNCLASSIFIED),
            ("Upper_case_code", CAUSE_UNCLASSIFIED),
            ("a_" + "b" * 63, CAUSE_UNCLASSIFIED),
            ("a_" + "b" * 62, "a_" + "b" * 62),
            ("code_with_trailing_\n", CAUSE_UNCLASSIFIED),
        ],
    )
    def test_code_is_safe(self, message: str, code: str) -> None:
        # Scenario: A free-text failure message never reaches the row or the event
        assert failure_cause_code(ValueError(message)) == code

    def test_validation_error_never_leaks_its_input(self) -> None:
        # Scenario: A free-text failure message never reaches the row or the event
        cause = failure_cause(_validation_error())

        assert cause == f"ValidationError: {CAUSE_UNCLASSIFIED}"
        assert _FREE_TEXT not in cause

    def test_cause_names_class_and_code(self) -> None:
        # Scenario: A ValueError during a resume is stored on the carousel row
        assert (
            failure_cause(ValueError(ERR_EN_TRANSLATION_PARSE_FAILED))
            == _CAUSE_TRANSLATION
        )
        assert failure_cause(RuntimeError("boom")) == "RuntimeError: unclassified"


async def _run_failing(error: BaseException) -> tuple[AsyncMock, AsyncMock, MagicMock]:
    service = MagicMock()
    service.get_workflow_state = AsyncMock(
        return_value={"current_phase": PHASE_OUTLINE}
    )
    service.resume_workflow = AsyncMock(side_effect=error)
    with (
        patch(
            f"{_RUNNER}.get_session_maker", return_value=_session_factory(AsyncMock())
        ),
        patch(f"{_RUNNER}._mark_background_resume_failed", new=AsyncMock()) as mark,
        patch(f"{_FAILURES}.record_workflow_outcome", new=AsyncMock()) as outcome,
        patch(f"{_FAILURES}.note_workflow_failure") as note,
        patch(f"{_RUNNER}.logger"),
    ):
        await execute_resume_run(service, _params())
    return mark, outcome, note


@pytest.mark.unit
@pytest.mark.asyncio
class TestResumeRecordsTheCause:
    async def test_value_error_cause_reaches_row_event_and_run(self) -> None:
        # Scenario: A ValueError during a resume is stored on the carousel row
        mark, outcome, note = await _run_failing(
            ValueError(ERR_EN_TRANSLATION_PARSE_FAILED)
        )

        params = mark.await_args.args[0]
        assert isinstance(params, MarkFailedParams)
        assert params.cause == _CAUSE_TRANSLATION
        assert params.message == ERR_BACKGROUND_RESUME_FAILED
        observation = outcome.await_args.args[0]
        assert isinstance(observation, WorkflowOutcomeObservation)
        assert observation.outcome == OUTCOME_FAILED
        assert observation.phase == PHASE_OUTLINE
        assert observation.error_type == "ValueError"
        assert observation.reason == ERR_EN_TRANSLATION_PARSE_FAILED
        note.assert_called_once_with(_CAUSE_TRANSLATION)

    async def test_free_text_value_error_is_unclassified(self) -> None:
        # Scenario: A free-text failure message never reaches the row or the event
        mark, outcome, note = await _run_failing(ValueError(_FREE_TEXT))

        assert mark.await_args.args[0].cause == f"ValueError: {CAUSE_UNCLASSIFIED}"
        assert outcome.await_args.args[0].reason == CAUSE_UNCLASSIFIED
        note.assert_called_once_with(f"ValueError: {CAUSE_UNCLASSIFIED}")

    async def test_sentence_constant_maps_to_its_code(self) -> None:
        # Scenario: A sentence-style error constant is mapped to its code
        mark, _outcome, _note = await _run_failing(ValueError(ERR_INVALID_JSON))

        assert mark.await_args.args[0].cause == f"ValueError: {CAUSE_INVALID_JSON}"

    async def test_unexpected_exception_cause_is_recorded(self) -> None:
        # Scenario: An unexpected exception during a resume is stored on the row too
        mark, outcome, note = await _run_failing(RuntimeError("boom"))

        assert mark.await_args.args[0].cause == "RuntimeError: unclassified"
        observation = outcome.await_args.args[0]
        assert observation.error_type == "RuntimeError"
        assert observation.reason == CAUSE_UNCLASSIFIED
        note.assert_called_once_with("RuntimeError: unclassified")


@pytest.mark.unit
@pytest.mark.asyncio
class TestFailedRowKeepsTheCause:
    async def test_row_gets_failed_status_and_error_message(self) -> None:
        # Scenario: A ValueError during a resume is stored on the carousel row
        project = MagicMock()
        project.phase_status = "in_progress"
        project.error_message = None
        db = AsyncMock()
        db.get = AsyncMock(return_value=project)
        service = MagicMock()
        service.publish_resume_error_event = AsyncMock()

        with (
            patch(f"{_RUNNER}.get_session_maker", return_value=_session_factory(db)),
            patch(f"{_RUNNER}.publish_run_finished", new=AsyncMock()),
        ):
            await _mark_background_resume_failed(
                MarkFailedParams(
                    service=service,
                    project_id=_PROJECT_ID,
                    message=ERR_BACKGROUND_RESUME_FAILED,
                    recoverable=True,
                    cause=_CAUSE_TRANSLATION,
                )
            )

        db.get.assert_awaited_once_with(CarouselProjectModel, _PROJECT_ID)
        assert project.phase_status == PHASE_STATUS_FAILED
        assert project.error_message == _CAUSE_TRANSLATION
        db.commit.assert_awaited_once()
        service.publish_resume_error_event.assert_awaited_once_with(
            _PROJECT_ID, message=ERR_BACKGROUND_RESUME_FAILED, recoverable=True
        )

    async def test_missing_row_is_skipped(self) -> None:
        # Scenario: A ValueError during a resume is stored on the carousel row
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        service = MagicMock()
        service.publish_resume_error_event = AsyncMock()

        with (
            patch(f"{_RUNNER}.get_session_maker", return_value=_session_factory(db)),
            patch(f"{_RUNNER}.publish_run_finished", new=AsyncMock()),
        ):
            await _mark_background_resume_failed(
                MarkFailedParams(
                    service=service,
                    project_id=_PROJECT_ID,
                    message=ERR_BACKGROUND_RESUME_FAILED,
                    recoverable=True,
                    cause=_CAUSE_TRANSLATION,
                )
            )

        db.commit.assert_not_awaited()
        service.publish_resume_error_event.assert_awaited_once()
