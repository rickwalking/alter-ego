"""Unit tests for AE-0315 run lifecycle: fence layer (b), events, heartbeat.

Feature: tests/features/carousel_run_progress_reaper.feature
Covers the checkpoint-commit fence semantics, the run.* SSE publishers, the
in-process run-stage registry, heartbeat write retry, and the typed 409 /
state-response run metadata.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from rag_backend.api.routes.carousels.editorial_workflow_routes_response import (
    RunMetadataInput,
    apply_run_metadata,
    build_editorial_workflow_state_response,
)
from rag_backend.api.routes.carousels.editorial_workflow_routes_validate import (
    ensure_resume_not_in_progress,
)
from rag_backend.application.services.carousel.carousel_run_stage import (
    clear_run_stage,
    get_run_stage,
    set_run_stage,
)
from rag_backend.application.services.carousel.editorial_workflow_run_events import (
    publish_run_finished,
    publish_run_stage_changed,
    publish_run_started,
)
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_RUN_IN_PROGRESS,
)
from rag_backend.domain.constants.carousel_run import (
    RUN_FINISHED_REASON_COMPLETED,
    RUN_STAGE_GENERATING,
    RUN_STAGE_VALIDATING,
    SSE_EVENT_RUN_FINISHED,
    SSE_EVENT_RUN_STAGE_CHANGED,
    SSE_EVENT_RUN_STARTED,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.models.carousel_conflict import CarouselConflictError
from rag_backend.domain.models.carousel_run import (
    CarouselRunContext,
    StaleRunEpochError,
    carousel_run_epoch_var,
    ensure_checkpoint_commit_allowed,
    register_run_epoch_reader,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.infrastructure import carousel_run_progress

_HUB_PATH = (
    "rag_backend.application.services.carousel.workflow_sse_hub.get_workflow_sse_hub"
)

_PROJECT_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(autouse=True)
def _reset_run_context():
    yield
    carousel_run_epoch_var.set(None)
    clear_run_stage(_PROJECT_ID)


def _stub_reader(current_epoch: int | None):
    async def _read(_project_id: str) -> int | None:
        return current_epoch

    return _read


@pytest.mark.asyncio
class TestCheckpointCommitFence:
    """Scenario: a reaped task cannot land checkpoint writes (layer b)."""

    async def test_stale_epoch_is_rejected(self) -> None:
        register_run_epoch_reader(_stub_reader(current_epoch=1))
        try:
            carousel_run_epoch_var.set(
                CarouselRunContext(project_id=_PROJECT_ID, epoch=0)
            )
            with pytest.raises(StaleRunEpochError):
                await ensure_checkpoint_commit_allowed(_PROJECT_ID)
        finally:
            register_run_epoch_reader(None)

    async def test_current_epoch_passes(self) -> None:
        register_run_epoch_reader(_stub_reader(current_epoch=1))
        try:
            carousel_run_epoch_var.set(
                CarouselRunContext(project_id=_PROJECT_ID, epoch=1)
            )
            await ensure_checkpoint_commit_allowed(_PROJECT_ID)
        finally:
            register_run_epoch_reader(None)

    async def test_unset_contextvar_passes_without_reading(self) -> None:
        # User/API contexts are never fenced (pinned r6).
        register_run_epoch_reader(_stub_reader(current_epoch=99))
        try:
            await ensure_checkpoint_commit_allowed(_PROJECT_ID)
        finally:
            register_run_epoch_reader(None)

    async def test_other_project_context_passes(self) -> None:
        register_run_epoch_reader(_stub_reader(current_epoch=99))
        try:
            carousel_run_epoch_var.set(
                CarouselRunContext(project_id=str(uuid.uuid4()), epoch=0)
            )
            await ensure_checkpoint_commit_allowed(_PROJECT_ID)
        finally:
            register_run_epoch_reader(None)


@pytest.mark.asyncio
class TestRunLifecycleEvents:
    """Scenario: banner updates live through run.* events."""

    async def test_run_started_payload(self) -> None:
        hub = AsyncMock()
        started = datetime(2026, 7, 10, 3, 39, tzinfo=UTC)
        with patch(_HUB_PATH, return_value=hub):
            await publish_run_started(_PROJECT_ID, PHASE_CONTENT, started)
        event = hub.publish.await_args.args[1]
        assert event["event"] == SSE_EVENT_RUN_STARTED
        assert event["phase"] == PHASE_CONTENT
        assert event["phase_status"] == PHASE_STATUS_IN_PROGRESS
        assert event["run_started_at"] == started.isoformat()

    async def test_stage_changed_updates_registry_and_publishes(self) -> None:
        hub = AsyncMock()
        with patch(_HUB_PATH, return_value=hub):
            await publish_run_stage_changed(_PROJECT_ID, RUN_STAGE_VALIDATING)
        assert get_run_stage(_PROJECT_ID) == RUN_STAGE_VALIDATING
        event = hub.publish.await_args.args[1]
        assert event["event"] == SSE_EVENT_RUN_STAGE_CHANGED
        assert event["run_stage"] == RUN_STAGE_VALIDATING

    async def test_run_finished_clears_stage_and_carries_reason(self) -> None:
        hub = AsyncMock()
        set_run_stage(_PROJECT_ID, RUN_STAGE_VALIDATING)
        with patch(_HUB_PATH, return_value=hub):
            await publish_run_finished(
                _PROJECT_ID,
                RUN_FINISHED_REASON_COMPLETED,
                final_phase_status=PHASE_STATUS_AWAITING_HUMAN,
            )
        assert get_run_stage(_PROJECT_ID) == RUN_STAGE_GENERATING  # fallback
        event = hub.publish.await_args.args[1]
        assert event["event"] == SSE_EVENT_RUN_FINISHED
        assert event["reason"] == RUN_FINISHED_REASON_COMPLETED
        assert event["phase_status"] == PHASE_STATUS_AWAITING_HUMAN


@pytest.mark.asyncio
class TestHeartbeatRetry:
    """Scenario: a single failed heartbeat write never causes a reap."""

    async def test_retries_transient_failure_then_succeeds(self, monkeypatch) -> None:
        attempts: list[int] = []

        async def _flaky(project_id: str, epoch: int) -> bool:
            attempts.append(epoch)
            if len(attempts) == 1:
                raise RuntimeError("transient blip")
            return True

        monkeypatch.setattr(carousel_run_progress, "write_run_heartbeat", _flaky)
        monkeypatch.setattr(
            carousel_run_progress, "_HEARTBEAT_RETRY_DELAY_SECONDS", 0.0
        )
        ok = await carousel_run_progress.write_run_heartbeat_with_retry(_PROJECT_ID, 0)
        assert ok is True
        assert len(attempts) == 2

    async def test_returns_false_after_exhausted_retries(self, monkeypatch) -> None:
        async def _always_failing(project_id: str, epoch: int) -> bool:
            raise RuntimeError("db down")

        monkeypatch.setattr(
            carousel_run_progress, "write_run_heartbeat", _always_failing
        )
        monkeypatch.setattr(
            carousel_run_progress, "_HEARTBEAT_RETRY_DELAY_SECONDS", 0.0
        )
        ok = await carousel_run_progress.write_run_heartbeat_with_retry(_PROJECT_ID, 0)
        assert ok is False


class TestTypedRunInProgressConflict:
    """Scenario: Resume attempt during a run explains itself."""

    def test_conflict_carries_run_started_at(self) -> None:
        started = datetime(2026, 7, 10, 3, 39, tzinfo=UTC)
        project = CarouselProjectModel(
            id=str(uuid.uuid4()),
            topic="t",
            audience="a",
            niche="n",
            phase_status=PHASE_STATUS_IN_PROGRESS,
        )
        project.run_started_at = started
        with pytest.raises(CarouselConflictError) as exc_info:
            ensure_resume_not_in_progress(project, None)
        conflict = exc_info.value.conflict
        assert conflict.code == CONFLICT_CODE_RUN_IN_PROGRESS
        assert conflict.run_started_at == started


class TestRunMetadataResponse:
    """Scenario: reload reconstructs the banner from workflow state."""

    def _response(self, phase_status: str):
        return build_editorial_workflow_state_response({
            "project_id": _PROJECT_ID,
            "current_phase": PHASE_CONTENT,
            "phase_status": phase_status,
        })

    def test_attached_while_in_progress(self) -> None:
        started = datetime(2026, 7, 10, 3, 39, tzinfo=UTC)
        response = apply_run_metadata(
            self._response(PHASE_STATUS_IN_PROGRESS),
            RunMetadataInput(run_started_at=started, run_stage=RUN_STAGE_VALIDATING),
        )
        assert response.run_started_at == started
        assert response.run_stage == RUN_STAGE_VALIDATING

    def test_omitted_when_not_in_progress(self) -> None:
        response = apply_run_metadata(
            self._response(PHASE_STATUS_AWAITING_HUMAN),
            RunMetadataInput(
                run_started_at=datetime.now(UTC),
                run_stage=RUN_STAGE_VALIDATING,
            ),
        )
        assert response.run_started_at is None
        assert response.run_stage is None


@pytest.mark.asyncio
class TestHeartbeatLockSafety:
    """AE-0320 scenarios (tests/features/carousel_run_lock_safety.feature)."""

    async def test_single_attempt_beat_never_raises_and_logs(self, monkeypatch) -> None:
        """Scenario: Stage-boundary beat is single-attempt and never raises."""
        from structlog.testing import capture_logs

        attempts: list[int] = []

        async def _always_failing(project_id: str, epoch: int) -> bool:
            attempts.append(epoch)
            raise RuntimeError("row lock timeout")

        monkeypatch.setattr(
            carousel_run_progress, "write_run_heartbeat", _always_failing
        )
        with capture_logs() as logs:
            ok = await carousel_run_progress.write_run_heartbeat_once(_PROJECT_ID, 0)

        assert ok is False
        assert len(attempts) == 1  # single attempt — no retry loop
        warned = [
            log for log in logs if log["event"] == "carousel_run_heartbeat_failed"
        ]
        assert len(warned) == 1

    async def test_single_attempt_beat_returns_write_result(self, monkeypatch) -> None:
        async def _ok(project_id: str, epoch: int) -> bool:
            return True

        monkeypatch.setattr(carousel_run_progress, "write_run_heartbeat", _ok)
        assert await carousel_run_progress.write_run_heartbeat_once(_PROJECT_ID, 0)

    async def test_heartbeat_applies_lock_timeout_on_postgres(self) -> None:
        """Scenario: Heartbeat write is bounded by a lock timeout on Postgres."""
        from unittest.mock import AsyncMock, MagicMock, patch

        session = AsyncMock()
        bind = MagicMock()
        bind.dialect.name = "postgresql"
        session.get_bind = MagicMock(return_value=bind)
        result = MagicMock()
        result.rowcount = 1
        session.execute = AsyncMock(return_value=result)

        @asynccontextmanager
        async def _fake_session():
            yield session

        factory = MagicMock(return_value=_fake_session())
        with patch.object(
            carousel_run_progress, "get_session_maker", return_value=factory
        ):
            ok = await carousel_run_progress.write_run_heartbeat(_PROJECT_ID, 0)

        assert ok is True
        first_stmt = str(session.execute.await_args_list[0].args[0])
        assert "lock_timeout" in first_stmt

    async def test_heartbeat_skips_lock_timeout_on_sqlite(self) -> None:
        """Scenario: Heartbeat write skips the lock timeout on SQLite."""
        from unittest.mock import AsyncMock, MagicMock, patch

        session = AsyncMock()
        bind = MagicMock()
        bind.dialect.name = "sqlite"
        session.get_bind = MagicMock(return_value=bind)
        result = MagicMock()
        result.rowcount = 1
        session.execute = AsyncMock(return_value=result)

        @asynccontextmanager
        async def _fake_session():
            yield session

        factory = MagicMock(return_value=_fake_session())
        with patch.object(
            carousel_run_progress, "get_session_maker", return_value=factory
        ):
            await carousel_run_progress.write_run_heartbeat(_PROJECT_ID, 0)

        for call in session.execute.await_args_list:
            assert "lock_timeout" not in str(call.args[0])
