"""Owner/admin HTTP integration for accepted manual recovery requests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.modules.generation_queue.domain.models import GenerationStatus
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from tests.integration.manual_reprocess_api_support import (
    RecoveryApiHarness,
    recovery_api_harness,
)
from tests.integration.manual_reprocess_support import (
    NOW,
    OLD,
    project_row,
    reprocess_audits,
    workflow_run_row,
)


@pytest.fixture(autouse=True)
def _relay_disabled(no_outbox_relay: object) -> None:
    del no_outbox_relay


@pytest_asyncio.fixture(loop_scope="function")
async def harness(tmp_path: Path) -> AsyncIterator[RecoveryApiHarness]:
    async with recovery_api_harness(tmp_path) as built:
        yield built


def _url(project_id: str) -> str:
    return f"/api/carousels/{project_id}/workflow/reprocess"


async def _seed_kind(harness: RecoveryApiHarness, kind: str) -> tuple[str, UUID | None]:
    project_id = str(uuid4())
    project = project_row(
        project_id,
        str(harness.owner.id),
        run_heartbeat_at=OLD if kind == "stale_running" else NOW,
    )
    runs = []
    run_id = None
    if kind != "orphan":
        statuses = {
            "dead_letter": GenerationStatus.DEAD_LETTER,
            "retry_wait": GenerationStatus.RETRY_WAIT,
            "stale_running": GenerationStatus.RUNNING,
        }
        row = workflow_run_row(project_id, statuses[kind])
        if kind == "retry_wait":
            row.next_attempt_at = NOW + timedelta(minutes=10)
        runs.append(row)
        run_id = row.id
    async with harness.sessions() as session:
        session.add(project)
        session.add_all(runs)
        await session.commit()
    return project_id, run_id


async def _post_project(
    harness: RecoveryApiHarness,
    project_id: str,
    run_id: UUID | None = None,
) -> object:
    payload: dict[str, object] = {"expected_version": 4}
    if run_id is not None:
        payload["run_id"] = str(run_id)
    return await harness.client.post(
        _url(project_id), json=payload, headers=harness.headers(harness.owner)
    )


@pytest.mark.parametrize(
    "kind", ["dead_letter", "retry_wait", "stale_running", "orphan"]
)
async def test_every_stuck_kind_returns_202_and_progress(
    harness: RecoveryApiHarness, kind: str
) -> None:
    """Scenario: Every required stuck kind is accepted without graph execution."""
    project_id, run_id = await _seed_kind(harness, kind)
    response = await _post_project(harness, project_id, run_id)
    assert response.status_code == 202
    body = response.json()
    assert body["outcome"] == "queued"
    assert body["run_id"]
    assert body["status"] == "queued"
    assert body["position"] is None
    assert body["eta_seconds"] is None
    assert body["lock_version"] == 5
    assert body["worker_notified"] is True
    assert body["stuck_kind"] == kind


async def test_sequential_double_click_returns_existing_and_one_audit(
    harness: RecoveryApiHarness,
) -> None:
    """Scenario: Sequential double click is idempotent before the version CAS."""
    project_id, run_id = await _seed_kind(harness, "dead_letter")
    first = await _post_project(harness, project_id, run_id)
    second = await _post_project(harness, project_id, run_id)
    async with harness.sessions() as session:
        audits = await reprocess_audits(session)
        active = await session.scalar(
            select(func.count())
            .select_from(GenerationRunModel)
            .where(GenerationRunModel.status.in_(("queued", "running", "retry_wait")))
        )
    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["outcome"] == "existing"
    assert second.json()["run_id"] == first.json()["run_id"]
    assert second.json()["lock_version"] == 5
    assert active == 1
    assert len(audits) == 1
    assert len(harness.notifier.notices) == 2


async def test_concurrent_double_click_shares_one_run_and_audit(
    harness: RecoveryApiHarness,
) -> None:
    """Scenario: Concurrent HTTP clicks return the same run with one audit."""
    project_id, run_id = await _seed_kind(harness, "dead_letter")
    responses = await asyncio.gather(
        _post_project(harness, project_id, run_id),
        _post_project(harness, project_id, run_id),
    )
    async with harness.sessions() as session:
        audits = await reprocess_audits(session)
        active = await session.scalar(
            select(func.count())
            .select_from(GenerationRunModel)
            .where(GenerationRunModel.status.in_(("queued", "running", "retry_wait")))
        )
    assert sorted(response.status_code for response in responses) == [200, 202], [
        response.text for response in responses
    ]
    assert {response.json()["run_id"] for response in responses} == {str(run_id)}
    assert active == 1
    assert len(audits) == 1
    assert len(harness.notifier.notices) == 2


async def test_audit_and_outbox_are_safe_and_no_graph_is_built(
    harness: RecoveryApiHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Acceptance writes only safe audit fields and never builds a graph."""
    from rag_backend.api.routes.carousels import editorial_workflow_routes_support

    def _forbidden_graph(*args: object) -> object:
        raise AssertionError("graph construction is forbidden")

    monkeypatch.setattr(
        editorial_workflow_routes_support,
        "build_editorial_workflow_service",
        _forbidden_graph,
    )
    project_id, run_id = await _seed_kind(harness, "dead_letter")
    response = await _post_project(harness, project_id, run_id)
    async with harness.sessions() as session:
        audits = await reprocess_audits(session)
        outbox = list((await session.scalars(select(EventOutboxModel))).all())
    assert response.status_code == 202
    assert len(audits) == len(outbox) == 1
    expected = {
        "actor_id": str(harness.owner.id),
        "project_id": project_id,
        "run_id": str(run_id),
        "stuck_kind": "dead_letter",
        "lock_version": 5,
    }
    assert audits[0].payload == expected
    assert outbox[0].payload == expected
    assert "Safe topic" not in response.text


async def test_notifier_failure_is_false_and_row_remains_durable(
    harness: RecoveryApiHarness,
) -> None:
    """Scenario: Maintenance failure is honest and never rolls back the run."""
    project_id, run_id = await _seed_kind(harness, "retry_wait")
    harness.notifier.error = RuntimeError("sensitive queue detail")
    response = await _post_project(harness, project_id, run_id)
    async with harness.sessions() as session:
        stored = await session.get(GenerationRunModel, run_id)
    assert response.status_code == 202
    assert response.json()["worker_notified"] is False
    assert "sensitive queue detail" not in response.text
    assert stored is not None
    assert stored.status == GenerationStatus.QUEUED.value


async def test_get_returns_capability_and_current_progress(
    harness: RecoveryApiHarness,
) -> None:
    """Scenario: Workspace GET exposes capability and current queued progress."""
    project_id, run_id = await _seed_kind(harness, "dead_letter")
    await _post_project(harness, project_id, run_id)
    response = await harness.client.get(
        _url(project_id), headers=harness.headers(harness.owner)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["can_reprocess"] is True
    assert body["refusal_code"] is None
    assert body["run_id"] == str(run_id)
    assert body["status"] == "queued"
    assert body["last_phase"] == "content"
    assert body["lock_version"] == 5
    assert body["position"] is None
    assert body["eta_seconds"] is None


async def test_admin_can_reprocess_projectless_run_with_status_cas(
    harness: RecoveryApiHarness,
) -> None:
    """Scenario: A projectless existing run uses generation-status CAS only."""
    row = workflow_run_row(
        str(uuid4()), GenerationStatus.RETRY_WAIT, carousel_project_id=None
    )
    async with harness.sessions() as session:
        session.add(row)
        await session.commit()
    response = await harness.client.post(
        f"/api/generation-runs/{row.id}/reprocess",
        json={},
        headers=harness.headers(harness.admin),
    )
    assert response.status_code == 202
    assert response.json()["run_id"] == str(row.id)
    assert response.json()["lock_version"] is None
