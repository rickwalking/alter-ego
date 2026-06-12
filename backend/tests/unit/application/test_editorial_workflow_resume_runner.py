"""Unit tests for background editorial workflow resume runner helpers."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.carousel.editorial_workflow_resume_runner import (
    BackgroundResumeParams,
    _background_tasks,
    _detect_resume_stuck,
    _execute_background_resume,
    _mark_background_resume_failed,
    _MarkFailedParams,
    _revert_background_resume_stuck,
    schedule_background_resume,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    ResumeWorkflowInput,
    resolve_background_resume_sse_error_message,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_FAILED,
    ERR_BACKGROUND_RESUME_STUCK,
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_REVISION_CAP_EXCEEDED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_REVISE,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel


def _make_params(
    action: str = REVIEW_ACTION_APPROVE,
    feedback: str | None = None,
    structured_feedback: dict[str, object] | None = None,
) -> BackgroundResumeParams:
    """Test helper — builds minimal BackgroundResumeParams."""
    return BackgroundResumeParams(
        project_id="test-project",
        action=action,
        reviewer_id="reviewer-1",
        feedback=feedback,
        project_title="Test carousel",
        structured_feedback=structured_feedback,
    )


def _make_session_factory(mock_db: AsyncMock) -> MagicMock:
    """Test helper — builds a fake session factory."""

    @asynccontextmanager
    async def fake_session():
        yield mock_db

    return MagicMock(return_value=fake_session())


@pytest.fixture(autouse=True)
def _clean_background_tasks():
    """Ensure _background_tasks is empty before/after each test."""
    _background_tasks.clear()
    yield
    _background_tasks.clear()


@pytest.mark.unit
class TestBackgroundResumeErrorAllowlist:
    """Scenario: Background resume failure publishes recoverable error event."""

    def test_internal_runtime_errors_are_redacted(self) -> None:
        assert (
            resolve_background_resume_sse_error_message("content generation failed")
            == ERR_BACKGROUND_RESUME_FAILED
        )

    def test_known_persona_errors_pass_through(self) -> None:
        assert (
            resolve_background_resume_sse_error_message(ERR_PERSONA_SCORE_TOO_LOW)
            == ERR_PERSONA_SCORE_TOO_LOW
        )


@pytest.mark.unit
class TestDetectResumeStuck:
    """Scenario: Background resume stuck detection for approve actions."""

    def test_approve_same_phase_awaiting_detects_stuck(self) -> None:
        """Given approve action and phase unchanged with awaiting_human,
        returns True."""
        result = _detect_resume_stuck(
            _make_params(REVIEW_ACTION_APPROVE),
            prior_phase="research",
            state={
                "current_phase": "research",
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            },
        )
        assert result is True

    def test_approve_phase_advances_not_stuck(self) -> None:
        """Given approve action and phase advances, returns False."""
        result = _detect_resume_stuck(
            _make_params(REVIEW_ACTION_APPROVE),
            prior_phase="research",
            state={
                "current_phase": "outline",
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            },
        )
        assert result is False

    def test_revise_same_phase_not_stuck(self) -> None:
        """Given revise action and phase unchanged, returns False
        (revise legitimately returns to same phase)."""
        result = _detect_resume_stuck(
            _make_params(REVIEW_ACTION_REVISE),
            prior_phase="research",
            state={
                "current_phase": "research",
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            },
        )
        assert result is False

    def test_empty_prior_phase_not_stuck(self) -> None:
        """Given no prior phase (first resume), returns False."""
        result = _detect_resume_stuck(
            _make_params(REVIEW_ACTION_APPROVE),
            prior_phase="",
            state={
                "current_phase": "research",
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            },
        )
        assert result is False

    def test_approve_different_phase_not_stuck(self) -> None:
        """Given approve action but phase changed, returns False."""
        result = _detect_resume_stuck(
            _make_params(REVIEW_ACTION_APPROVE),
            prior_phase="research",
            state={"current_phase": "research", "phase_status": "in_progress"},
        )
        assert result is False

    def test_reject_same_phase_not_stuck(self) -> None:
        """AE-0027: Given reject action and phase unchanged, returns False
        (reject legitimately returns to same phase)."""
        result = _detect_resume_stuck(
            _make_params(REVIEW_ACTION_REJECT),
            prior_phase="research",
            state={
                "current_phase": "research",
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            },
        )
        assert result is False


@pytest.mark.unit
class TestScheduleBackgroundResume:
    """Scenario: schedule_background_resume fires and tracks background task."""

    def test_creates_task_with_correct_name_and_coroutine(self) -> None:
        """Given service and params, creates asyncio task with correct name and adds to set."""
        params = _make_params()
        service = MagicMock()

        mock_task = MagicMock()
        mock_bg_tasks = set()

        with (
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner._background_tasks",
                mock_bg_tasks,
            ),
            patch("asyncio.create_task", return_value=mock_task) as mock_create_task,
        ):
            schedule_background_resume(service, params)

            mock_create_task.assert_called_once()
            args, kwargs = mock_create_task.call_args
            assert asyncio.iscoroutine(args[0])
            assert kwargs == {"name": f"workflow-resume-{params.project_id}"}
            assert mock_task in mock_bg_tasks
            mock_task.add_done_callback.assert_called_once_with(mock_bg_tasks.discard)


@pytest.mark.unit
class TestExecuteBackgroundResume:
    """Scenario: _execute_background_resume runs workflow and handles all branches."""

    @pytest.mark.asyncio
    async def test_happy_path_commits_and_publishes_sse(self) -> None:
        """Given successful resume, commits DB and publishes SSE updates."""
        params = _make_params()
        service = MagicMock()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        session_factory = _make_session_factory(mock_db)

        prior_state = {"current_phase": "research"}
        new_state = {
            "current_phase": "outline",
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        }

        service.get_workflow_state = AsyncMock(return_value=prior_state)
        service.resume_workflow = AsyncMock(return_value=new_state)

        with (
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
                return_value=session_factory,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.publish_workflow_sse_updates",
                new_callable=AsyncMock,
            ) as mock_sse,
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner._detect_resume_stuck",
                return_value=False,
            ) as mock_detect,
        ):
            await _execute_background_resume(service, params)

            service.get_workflow_state.assert_awaited_once_with(params.project_id)

            service.resume_workflow.assert_awaited_once()
            actual_input = service.resume_workflow.await_args[0][0]
            expected_input = ResumeWorkflowInput(
                project_id=params.project_id,
                action=params.action,
                reviewer_id=params.reviewer_id,
                feedback=params.feedback,
                db=mock_db,
                persona=None,
                project_title=params.project_title,
                structured_feedback=params.structured_feedback,
            )
            assert actual_input == expected_input

            mock_detect.assert_called_once_with(params, "research", new_state)
            mock_db.commit.assert_awaited_once()
            mock_sse.assert_awaited_once_with(params.project_id, new_state)

    @pytest.mark.asyncio
    async def test_happy_path_with_feedback_and_structured_feedback(self) -> None:
        """Given params with feedback and structured_feedback, passes them exactly."""
        params = _make_params(
            feedback="great work",
            structured_feedback={"key": "value"},
        )
        service = MagicMock()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        session_factory = _make_session_factory(mock_db)

        new_state = {
            "current_phase": "outline",
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        }

        service.get_workflow_state = AsyncMock(return_value=None)
        service.resume_workflow = AsyncMock(return_value=new_state)

        with (
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
                return_value=session_factory,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.publish_workflow_sse_updates",
                new_callable=AsyncMock,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner._detect_resume_stuck",
                return_value=False,
            ),
        ):
            await _execute_background_resume(service, params)

            service.resume_workflow.assert_awaited_once()
            actual_input = service.resume_workflow.await_args[0][0]
            expected_input = ResumeWorkflowInput(
                project_id=params.project_id,
                action=params.action,
                reviewer_id=params.reviewer_id,
                feedback="great work",
                db=mock_db,
                persona=None,
                project_title=params.project_title,
                structured_feedback={"key": "value"},
            )
            assert actual_input == expected_input

    @pytest.mark.asyncio
    async def test_prior_state_none_sets_empty_prior_phase(self) -> None:
        """Given no prior state, prior_phase is empty string."""
        params = _make_params()
        service = MagicMock()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        session_factory = _make_session_factory(mock_db)

        new_state = {
            "current_phase": "outline",
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        }

        service.get_workflow_state = AsyncMock(return_value=None)
        service.resume_workflow = AsyncMock(return_value=new_state)

        with (
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
                return_value=session_factory,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.publish_workflow_sse_updates",
                new_callable=AsyncMock,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner._detect_resume_stuck",
                return_value=False,
            ) as mock_detect,
        ):
            await _execute_background_resume(service, params)

            mock_detect.assert_called_once_with(params, "", new_state)

    @pytest.mark.asyncio
    async def test_empty_prior_state_dict_sets_empty_prior_phase(self) -> None:
        """Given empty prior state dict, prior_phase is empty string."""
        params = _make_params()
        service = MagicMock()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        session_factory = _make_session_factory(mock_db)

        new_state = {
            "current_phase": "outline",
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        }

        service.get_workflow_state = AsyncMock(return_value={})
        service.resume_workflow = AsyncMock(return_value=new_state)

        with (
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
                return_value=session_factory,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.publish_workflow_sse_updates",
                new_callable=AsyncMock,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner._detect_resume_stuck",
                return_value=False,
            ) as mock_detect,
        ):
            await _execute_background_resume(service, params)

            mock_detect.assert_called_once_with(params, "", new_state)

    @pytest.mark.asyncio
    async def test_stuck_detected_reverts_and_returns_early(self) -> None:
        """Given stuck detected, reverts and does not commit or publish SSE."""
        params = _make_params()
        service = MagicMock()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        session_factory = _make_session_factory(mock_db)

        prior_state = {"current_phase": "research"}
        new_state = {
            "current_phase": "research",
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        }

        service.get_workflow_state = AsyncMock(return_value=prior_state)
        service.resume_workflow = AsyncMock(return_value=new_state)

        with (
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
                return_value=session_factory,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.publish_workflow_sse_updates",
                new_callable=AsyncMock,
            ) as mock_sse,
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner._detect_resume_stuck",
                return_value=True,
            ) as mock_detect,
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner._revert_background_resume_stuck",
                new_callable=AsyncMock,
            ) as mock_revert,
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.logger",
            ) as mock_logger,
        ):
            await _execute_background_resume(service, params)

            mock_detect.assert_called_once_with(params, "research", new_state)
            mock_revert.assert_awaited_once_with(service, params.project_id, "research")
            mock_logger.warning.assert_called_once_with(
                "background_resume_stuck",
                project_id=params.project_id,
                phase="research",
                action=params.action,
            )
            mock_db.commit.assert_not_awaited()
            mock_sse.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_value_error_revision_cap_exceeded_rolls_back_non_recoverable(
        self,
    ) -> None:
        """Given ValueError with revision_cap_exceeded, rolls back and marks non-recoverable."""
        params = _make_params()
        service = MagicMock()
        mock_db = AsyncMock()
        mock_db.rollback = AsyncMock()
        session_factory = _make_session_factory(mock_db)

        service.get_workflow_state = AsyncMock(
            return_value={"current_phase": "research"}
        )
        service.resume_workflow = AsyncMock(
            side_effect=ValueError(ERR_REVISION_CAP_EXCEEDED)
        )

        with (
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
                return_value=session_factory,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.resolve_background_resume_sse_error_message",
                return_value=ERR_REVISION_CAP_EXCEEDED,
            ) as mock_resolve,
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner._mark_background_resume_failed",
                new_callable=AsyncMock,
            ) as mock_mark,
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.logger",
            ) as mock_logger,
        ):
            await _execute_background_resume(service, params)

            mock_db.rollback.assert_awaited_once()
            mock_resolve.assert_called_once_with(ERR_REVISION_CAP_EXCEEDED)
            mock_mark.assert_awaited_once_with(
                _MarkFailedParams(
                    service=service,
                    project_id=params.project_id,
                    message=ERR_REVISION_CAP_EXCEEDED,
                    recoverable=False,
                )
            )
            mock_logger.warning.assert_called_once_with(
                "background_resume_validation_failed",
                project_id=params.project_id,
                detail=ERR_REVISION_CAP_EXCEEDED,
            )

    @pytest.mark.asyncio
    async def test_value_error_persona_score_too_low_rolls_back_recoverable(
        self,
    ) -> None:
        """Given ValueError with persona_score_too_low, rolls back and marks recoverable."""
        params = _make_params()
        service = MagicMock()
        mock_db = AsyncMock()
        mock_db.rollback = AsyncMock()
        session_factory = _make_session_factory(mock_db)

        service.get_workflow_state = AsyncMock(
            return_value={"current_phase": "research"}
        )
        service.resume_workflow = AsyncMock(
            side_effect=ValueError(ERR_PERSONA_SCORE_TOO_LOW)
        )

        with (
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
                return_value=session_factory,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.resolve_background_resume_sse_error_message",
                return_value=ERR_PERSONA_SCORE_TOO_LOW,
            ) as mock_resolve,
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner._mark_background_resume_failed",
                new_callable=AsyncMock,
            ) as mock_mark,
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.logger",
            ) as mock_logger,
        ):
            await _execute_background_resume(service, params)

            mock_db.rollback.assert_awaited_once()
            mock_resolve.assert_called_once_with(ERR_PERSONA_SCORE_TOO_LOW)
            mock_mark.assert_awaited_once_with(
                _MarkFailedParams(
                    service=service,
                    project_id=params.project_id,
                    message=ERR_PERSONA_SCORE_TOO_LOW,
                    recoverable=True,
                )
            )
            mock_logger.warning.assert_called_once_with(
                "background_resume_validation_failed",
                project_id=params.project_id,
                detail=ERR_PERSONA_SCORE_TOO_LOW,
            )

    @pytest.mark.asyncio
    async def test_value_error_other_message_rolls_back_recoverable(self) -> None:
        """Given ValueError with unknown message, rolls back and marks recoverable."""
        params = _make_params()
        service = MagicMock()
        mock_db = AsyncMock()
        mock_db.rollback = AsyncMock()
        session_factory = _make_session_factory(mock_db)

        service.get_workflow_state = AsyncMock(
            return_value={"current_phase": "research"}
        )
        service.resume_workflow = AsyncMock(side_effect=ValueError("some error"))

        with (
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
                return_value=session_factory,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.resolve_background_resume_sse_error_message",
                return_value=ERR_BACKGROUND_RESUME_FAILED,
            ) as mock_resolve,
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner._mark_background_resume_failed",
                new_callable=AsyncMock,
            ) as mock_mark,
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.logger",
            ) as mock_logger,
        ):
            await _execute_background_resume(service, params)

            mock_db.rollback.assert_awaited_once()
            mock_resolve.assert_called_once_with("some error")
            mock_mark.assert_awaited_once_with(
                _MarkFailedParams(
                    service=service,
                    project_id=params.project_id,
                    message=ERR_BACKGROUND_RESUME_FAILED,
                    recoverable=True,
                )
            )
            mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_generic_exception_rolls_back_with_failed_message(self) -> None:
        """Given generic Exception, rolls back and marks with background_resume_failed."""
        params = _make_params()
        service = MagicMock()
        mock_db = AsyncMock()
        mock_db.rollback = AsyncMock()
        session_factory = _make_session_factory(mock_db)

        service.get_workflow_state = AsyncMock(
            return_value={"current_phase": "research"}
        )
        service.resume_workflow = AsyncMock(side_effect=RuntimeError("boom"))

        with (
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
                return_value=session_factory,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner._mark_background_resume_failed",
                new_callable=AsyncMock,
            ) as mock_mark,
            patch(
                "rag_backend.application.services.carousel.editorial_workflow_resume_runner.logger",
            ) as mock_logger,
        ):
            await _execute_background_resume(service, params)

            mock_db.rollback.assert_awaited_once()
            mock_mark.assert_awaited_once_with(
                _MarkFailedParams(
                    service=service,
                    project_id=params.project_id,
                    message=ERR_BACKGROUND_RESUME_FAILED,
                    recoverable=True,
                )
            )
            mock_logger.exception.assert_called_once_with(
                "background_resume_failed",
                project_id=params.project_id,
            )


@pytest.mark.unit
class TestMarkBackgroundResumeFailed:
    """AE-0027: _mark_background_resume_failed updates DB and publishes error."""

    @pytest.mark.asyncio
    async def test_updates_project_phase_status_and_publishes_error(self) -> None:
        """Given existing project, sets phase_status to failed and publishes error."""
        project = MagicMock()
        project.phase_status = "in_progress"
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=project)
        mock_db.commit = AsyncMock()

        session_factory = _make_session_factory(mock_db)

        service = MagicMock()
        service.publish_resume_error_event = AsyncMock()

        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
            return_value=session_factory,
        ):
            await _mark_background_resume_failed(
                _MarkFailedParams(
                    service=service,
                    project_id="proj-1",
                    message=ERR_BACKGROUND_RESUME_FAILED,
                    recoverable=True,
                )
            )

        assert project.phase_status == PHASE_STATUS_FAILED
        mock_db.get.assert_awaited_once_with(CarouselProjectModel, "proj-1")
        mock_db.commit.assert_awaited_once()
        service.publish_resume_error_event.assert_awaited_once_with(
            "proj-1",
            message=ERR_BACKGROUND_RESUME_FAILED,
            recoverable=True,
        )

    @pytest.mark.asyncio
    async def test_skips_db_update_when_project_none(self) -> None:
        """Given no project, skips DB update but still publishes error."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        mock_db.commit = AsyncMock()

        session_factory = _make_session_factory(mock_db)

        service = MagicMock()
        service.publish_resume_error_event = AsyncMock()

        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
            return_value=session_factory,
        ):
            await _mark_background_resume_failed(
                _MarkFailedParams(
                    service=service,
                    project_id="proj-1",
                    message=ERR_BACKGROUND_RESUME_FAILED,
                    recoverable=True,
                )
            )

        mock_db.get.assert_awaited_once_with(CarouselProjectModel, "proj-1")
        mock_db.commit.assert_not_awaited()
        service.publish_resume_error_event.assert_awaited_once_with(
            "proj-1",
            message=ERR_BACKGROUND_RESUME_FAILED,
            recoverable=True,
        )

    @pytest.mark.asyncio
    async def test_publishes_non_recoverable_error(self) -> None:
        """Given recoverable=False, publishes error with recoverable=False."""
        project = MagicMock()
        project.phase_status = "in_progress"
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=project)
        mock_db.commit = AsyncMock()

        session_factory = _make_session_factory(mock_db)

        service = MagicMock()
        service.publish_resume_error_event = AsyncMock()

        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
            return_value=session_factory,
        ):
            await _mark_background_resume_failed(
                _MarkFailedParams(
                    service=service,
                    project_id="proj-1",
                    message=ERR_REVISION_CAP_EXCEEDED,
                    recoverable=False,
                )
            )

        assert project.phase_status == PHASE_STATUS_FAILED
        mock_db.commit.assert_awaited_once()
        service.publish_resume_error_event.assert_awaited_once_with(
            "proj-1",
            message=ERR_REVISION_CAP_EXCEEDED,
            recoverable=False,
        )


@pytest.mark.unit
class TestRevertBackgroundResumeStuck:
    """AE-0027: _revert_background_resume_stuck reverts DB and publishes error."""

    @pytest.mark.asyncio
    async def test_reverts_db_phase_status_to_awaiting_human(self) -> None:
        """Given a stuck project, _revert_background_resume_stuck SHALL
        set DB phase_status back to awaiting_human."""
        project = MagicMock()
        project.phase_status = "in_progress"
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=project)
        mock_db.commit = AsyncMock()

        session_factory = _make_session_factory(mock_db)

        service = MagicMock()
        service.publish_resume_error_event = AsyncMock()

        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
            return_value=session_factory,
        ):
            await _revert_background_resume_stuck(service, "proj-1", "research")

        assert project.phase_status == PHASE_STATUS_AWAITING_HUMAN
        mock_db.get.assert_awaited_once_with(CarouselProjectModel, "proj-1")
        mock_db.commit.assert_awaited_once()
        service.publish_resume_error_event.assert_awaited_once_with(
            "proj-1",
            message=ERR_BACKGROUND_RESUME_STUCK,
            recoverable=True,
        )

    @pytest.mark.asyncio
    async def test_publishes_stuck_error_event(self) -> None:
        """Given a stuck project, _revert_background_resume_stuck SHALL
        publish an error SSE event with ERR_BACKGROUND_RESUME_STUCK."""
        project = MagicMock()
        project.phase_status = "in_progress"
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=project)
        mock_db.commit = AsyncMock()

        session_factory = _make_session_factory(mock_db)

        service = MagicMock()
        service.publish_resume_error_event = AsyncMock()

        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
            return_value=session_factory,
        ):
            await _revert_background_resume_stuck(service, "proj-1", "research")

        service.publish_resume_error_event.assert_awaited_once_with(
            "proj-1",
            message=ERR_BACKGROUND_RESUME_STUCK,
            recoverable=True,
        )

    @pytest.mark.asyncio
    async def test_skips_db_update_when_project_none(self) -> None:
        """Given no project, skips DB update but still publishes error."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        mock_db.commit = AsyncMock()

        session_factory = _make_session_factory(mock_db)

        service = MagicMock()
        service.publish_resume_error_event = AsyncMock()

        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_resume_runner.get_session_maker",
            return_value=session_factory,
        ):
            await _revert_background_resume_stuck(service, "proj-1", "research")

        mock_db.get.assert_awaited_once_with(CarouselProjectModel, "proj-1")
        mock_db.commit.assert_not_awaited()
        service.publish_resume_error_event.assert_awaited_once_with(
            "proj-1",
            message=ERR_BACKGROUND_RESUME_STUCK,
            recoverable=True,
        )
