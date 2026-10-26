"""HTTP authorization and stable refusals for manual recovery."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_PENDING,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import RefusalCode
from rag_backend.modules.generation_queue.domain.models import GenerationStatus
from rag_backend.modules.generation_queue.infrastructure.drive_lock import (
    PostgresDriveLock,
)
from tests.integration.manual_reprocess_api_support import (
    RecoveryApiHarness,
    recovery_api_harness,
)
from tests.integration.manual_reprocess_support import (
    OLD,
    project_row,
    reprocess_audits,
    workflow_run_row,
)
from tests.unit.modules.generation_queue.manual_recovery_fakes import FakeDriveLock


@pytest.fixture(autouse=True)
def _relay_disabled(no_outbox_relay: object) -> None:
    del no_outbox_relay


@pytest_asyncio.fixture(loop_scope="function")
async def harness(tmp_path: Path) -> AsyncIterator[RecoveryApiHarness]:
    async with recovery_api_harness(tmp_path) as built:
        yield built


def _url(project_id: str) -> str:
    return f"/api/carousels/{project_id}/workflow/reprocess"


async def _dead_project(harness: RecoveryApiHarness) -> tuple[str, UUID]:
    project_id = str(uuid4())
    row = workflow_run_row(project_id, GenerationStatus.DEAD_LETTER)
    async with harness.sessions() as session:
        session.add_all([
            project_row(
                project_id,
                str(harness.owner.id),
                assigned_reviewer_id=str(harness.reviewer.id),
            ),
            row,
        ])
        await session.commit()
    return project_id, row.id


@pytest.mark.parametrize("actor", ["owner", "admin"])
async def test_project_endpoint_allows_owner_and_admin(
    harness: RecoveryApiHarness, actor: str
) -> None:
    """Scenario: Only the project owner or an admin may reprocess."""
    project_id, run_id = await _dead_project(harness)
    user = harness.owner if actor == "owner" else harness.admin
    response = await harness.client.post(
        _url(project_id),
        json={"expected_version": 4, "run_id": str(run_id)},
        headers=harness.headers(user),
    )
    assert response.status_code == 202


async def test_assigned_reviewer_cannot_reprocess_or_read_capability(
    harness: RecoveryApiHarness,
) -> None:
    """Scenario: Workflow reviewer access does not grant recovery ownership."""
    project_id, run_id = await _dead_project(harness)
    headers = harness.headers(harness.reviewer)
    post = await harness.client.post(
        _url(project_id),
        json={"expected_version": 4, "run_id": str(run_id)},
        headers=headers,
    )
    get = await harness.client.get(_url(project_id), headers=headers)
    async with harness.sessions() as session:
        audits = await reprocess_audits(session)
    assert post.status_code == get.status_code == 403
    assert audits == []
    assert harness.notifier.notices == []


@pytest.mark.parametrize("actor", ["owner", "reviewer"])
async def test_run_endpoint_is_admin_only(
    harness: RecoveryApiHarness, actor: str
) -> None:
    """Scenario: Even the project owner cannot use the admin run endpoint."""
    _, run_id = await _dead_project(harness)
    user = harness.owner if actor == "owner" else harness.reviewer
    response = await harness.client.post(
        f"/api/generation-runs/{run_id}/reprocess",
        json={},
        headers=harness.headers(user),
    )
    assert response.status_code == 403


async def _seed_refusal(
    harness: RecoveryApiHarness, case: str
) -> tuple[str, UUID | None, int]:
    project_id = str(uuid4())
    overrides: dict[str, object] = {}
    status = None
    expected = 4
    if case == RefusalCode.OWNER_WAITING.value:
        overrides["phase_status"] = PHASE_STATUS_AWAITING_HUMAN
    elif case == RefusalCode.NORMAL_QUEUED.value:
        status = GenerationStatus.QUEUED
    elif case == RefusalCode.DISPATCHER_GRACE.value:
        overrides["updated_at"] = datetime.now(UTC)
    elif case == RefusalCode.FRESH_RUNNING.value:
        status = GenerationStatus.RUNNING
        overrides["run_heartbeat_at"] = datetime.now(UTC)
    elif case == RefusalCode.NULL_HEARTBEAT.value:
        status = GenerationStatus.RUNNING
        overrides["run_heartbeat_at"] = None
    elif case == RefusalCode.DRIVE_ACTIVE.value:
        status = GenerationStatus.RUNNING
        overrides["run_heartbeat_at"] = OLD
    elif case == RefusalCode.UNSUPPORTED.value:
        overrides["phase_status"] = PHASE_STATUS_PENDING
    elif case == RefusalCode.STALE_VERSION.value:
        status = GenerationStatus.DEAD_LETTER
        expected = 3
    project = project_row(project_id, str(harness.owner.id), **overrides)
    row = workflow_run_row(project_id, status) if status is not None else None
    async with harness.sessions() as session:
        session.add(project)
        if row is not None:
            session.add(row)
        await session.commit()
    return project_id, row.id if row is not None else None, expected


@pytest.mark.parametrize(
    "case",
    [
        RefusalCode.OWNER_WAITING.value,
        RefusalCode.NORMAL_QUEUED.value,
        RefusalCode.DISPATCHER_GRACE.value,
        RefusalCode.FRESH_RUNNING.value,
        RefusalCode.NULL_HEARTBEAT.value,
        RefusalCode.DRIVE_ACTIVE.value,
        RefusalCode.UNSUPPORTED.value,
        RefusalCode.STALE_VERSION.value,
    ],
)
async def test_every_refusal_is_stable_and_has_no_side_effects(
    harness: RecoveryApiHarness,
    case: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Not stuck work is refused with a reason"""
    project_id, run_id, expected = await _seed_refusal(harness, case)
    if case == RefusalCode.DRIVE_ACTIVE.value:
        lock = FakeDriveLock(busy=True)
        monkeypatch.setattr(
            PostgresDriveLock, "hold", lambda _self, keys: lock.hold(keys)
        )
    payload: dict[str, object] = {"expected_version": expected}
    if run_id is not None:
        payload["run_id"] = str(run_id)
    response = await harness.client.post(
        _url(project_id), json=payload, headers=harness.headers(harness.owner)
    )
    async with harness.sessions() as session:
        audits = await reprocess_audits(session)
    assert response.status_code == 409
    assert response.json()["detail"] == case
    assert audits == []
    assert harness.notifier.notices == []


async def test_cross_owner_existing_run_is_rejected(
    harness: RecoveryApiHarness,
) -> None:
    """Scenario: A cross-owner existing run is rejected"""
    own_project_id, _ = await _dead_project(harness)
    other_project_id = str(uuid4())
    other_run = workflow_run_row(
        other_project_id,
        GenerationStatus.DEAD_LETTER,
        payload={"manual_origin": "carousel_reprocess"},
    )
    async with harness.sessions() as session:
        session.add_all([
            project_row(other_project_id, str(harness.reviewer.id)),
            other_run,
        ])
        await session.commit()
    response = await harness.client.post(
        _url(own_project_id),
        json={"expected_version": 4, "run_id": str(other_run.id)},
        headers=harness.headers(harness.owner),
    )
    async with harness.sessions() as session:
        audits = await reprocess_audits(session)
    assert response.status_code == 404
    assert audits == []
    assert harness.notifier.notices == []


async def test_admin_project_version_is_checked_when_supplied(
    harness: RecoveryApiHarness,
) -> None:
    """Scenario: Optional project expected_version is enforced on the run route."""
    _, run_id = await _dead_project(harness)
    response = await harness.client.post(
        f"/api/generation-runs/{run_id}/reprocess",
        json={"expected_version": 3},
        headers=harness.headers(harness.admin),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == RefusalCode.STALE_VERSION.value


async def test_unknown_run_is_404_without_invented_recovery_id(
    harness: RecoveryApiHarness,
) -> None:
    """Scenario: Display-only or unknown ids never synthesize recovery work."""
    response = await harness.client.post(
        f"/api/generation-runs/{uuid4()}/reprocess",
        json={},
        headers=harness.headers(harness.admin),
    )
    assert response.status_code == 404
