"""Unit tests for the AE-0288 reopen ops script's safety guard.

The guard must reopen ONLY threads that are terminated (no pending node) AND
approved for publish — never an in-progress / paused / non-approved carousel.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from rag_backend.domain.constants.carousel_workflow import (
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "reopen_carousel_for_resend.py"
)


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("reopen_for_resend", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
class TestReopenEligibilityGuard:
    def test_eligible_when_terminated_and_approved(self) -> None:
        guard = _load_script()._is_terminated_and_approved
        snapshot = SimpleNamespace(
            next=(),
            values={"workflow_status": WORKFLOW_STATUS_APPROVED_FOR_PUBLISH},
        )
        assert guard(snapshot) is True

    def test_not_eligible_when_still_has_pending_node(self) -> None:
        guard = _load_script()._is_terminated_and_approved
        snapshot = SimpleNamespace(
            next=("approved_hold",),
            values={"workflow_status": WORKFLOW_STATUS_APPROVED_FOR_PUBLISH},
        )
        assert guard(snapshot) is False

    def test_not_eligible_when_not_approved(self) -> None:
        guard = _load_script()._is_terminated_and_approved
        snapshot = SimpleNamespace(next=(), values={"workflow_status": "draft"})
        assert guard(snapshot) is False

    def test_not_eligible_when_empty(self) -> None:
        guard = _load_script()._is_terminated_and_approved
        snapshot = SimpleNamespace(next=(), values={})
        assert guard(snapshot) is False
