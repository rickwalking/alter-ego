"""A Telegram review tap after the carousel was rejected closes the run.

Feature: tests/features/reject_bumps_lock_version_ae0604.feature
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from rag_backend.modules.autopilot.cover_constants import ANSWER_REVIEW_REPLACED
from rag_backend.modules.autopilot.domain.gate import GateSnapshot
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.recovery_constants import REASON_CAROUSEL_REJECTED
from rag_backend.modules.autopilot.webhook_constants import TEXT_REJECTED
from rag_backend.modules.editorial.public import PHASE_STATUS_REJECTED
from tests.unit.modules.autopilot.test_owner_actions import (
    _action,
    _Editorial,
    _handle,
    _snapshot,
    _tap,
    _world,
)

_S = AutopilotRunState
_REVIEW_MESSAGE = 9
_REJECTED_AT = 5


def _rejected(monkeypatch: pytest.MonkeyPatch, editorial: _Editorial) -> None:
    """The carousel as the approve reads it: rejected, one version past the review."""

    async def _read_gate(project_id: str) -> GateSnapshot:
        del project_id
        return replace(
            _snapshot(), phase_status=PHASE_STATUS_REJECTED, lock_version=_REJECTED_AT
        )

    monkeypatch.setattr(editorial, "read_gate", _read_gate)


def _on(update: WebhookUpdate, message_id: int) -> WebhookUpdate:
    return replace(update, message_id=message_id)


@pytest.mark.unit
class TestReviewTapAfterReject:
    # Scenario: A Telegram review tap after a reject closes the run
    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ["pubnow", "approve", "sched"])
    async def test_a_tap_on_a_rejected_carousel_closes_the_run(
        self, monkeypatch: pytest.MonkeyPatch, kind: str
    ) -> None:
        world = _world()
        _rejected(monkeypatch, world.editorial)

        await _handle(world, _on(_tap(1, _action(kind, world)), _REVIEW_MESSAGE))

        assert world.editorial.resumes == []
        assert world.release.ids == []
        assert world.runs.run.state is _S.REJECTED
        assert world.runs.run.state_reason == REASON_CAROUSEL_REJECTED
        assert world.messenger.answers[-1].text == ANSWER_REVIEW_REPLACED
        assert world.messenger.edits[-1].text == TEXT_REJECTED
