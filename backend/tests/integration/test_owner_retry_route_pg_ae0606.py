"""The website Retry route on Postgres, over a real checkpoint.

Feature: tests/features/carousel_owner_retry_ae0606.feature
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from rag_backend.domain.models import UserRole
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.owner_retry_support import retry_audits, staged_runs
from tests.integration.pg_schema_support import requires_postgres
from tests.integration.test_reject_bumps_lock_version_pg_ae0604 import (
    _app,
    _owner_reads,
    _Rig,
    _row,
    _sessions,
    _sweep,
    _waiting_carousel,
)

pytestmark = pytest.mark.usefixtures("no_outbox_relay", "asset_dirs")


def _path(project_id: str) -> str:
    return f"/api/carousels/{project_id}/workflow/retry"


async def _retry(rig: _Rig, project_id: str, version: int) -> tuple[int, dict]:
    response = await rig.client.post(
        _path(project_id), json={"expected_version": version}
    )
    return response.status_code, response.json()


async def _rejected(rig: _Rig) -> tuple[str, int]:
    project_id = await _waiting_carousel(rig)
    read_at = await _owner_reads(rig, project_id)
    assert await _sweep(rig) == 1
    return project_id, read_at


async def _staged(rig: _Rig, project_id: str) -> list[GenerationRunModel]:
    async with _sessions(rig)() as session:
        return await staged_runs(session, project_id)


# Scenario: Retry on a rejected carousel re-runs the phase it was rejected at
# Scenario: The retry capability is read without any change
@requires_postgres
@pytest.mark.asyncio
async def test_a_rejected_carousel_is_retried_from_the_website() -> None:
    async with _app() as rig:
        project_id, read_at = await _rejected(rig)
        capability = await rig.client.get(_path(project_id))

        status_code, body = await _retry(rig, project_id, read_at + 1)

        assert capability.status_code == 200, capability.text
        assert capability.json()["can_retry"] is True
        assert capability.json()["retry_kind"] == "redrive"
        assert status_code == 202, body
        assert body["retry_kind"] == "redrive"
        assert body["phase_status"] == "in_progress"
        assert body["lock_version"] == read_at + 2
        row = await _row(rig, project_id)
        assert (row.phase_status, row.status) == ("in_progress", "pending")
        runs = await _staged(rig, project_id)
        assert [run.payload["action"] for run in runs] == ["redrive"]
        async with _sessions(rig)() as session:
            audits = await retry_audits(session)
        assert [audit.payload["surface"] for audit in audits] == ["web"]
        assert audits[0].payload["reason"] == "carousel_rejected"


# Scenario: A double tap ends in run_in_progress
@requires_postgres
@pytest.mark.asyncio
async def test_a_second_website_retry_is_refused() -> None:
    async with _app() as rig:
        project_id, read_at = await _rejected(rig)
        first, _ = await _retry(rig, project_id, read_at + 1)

        status_code, body = await _retry(rig, project_id, read_at + 2)

        assert first == 202
        assert status_code == 409
        assert body["detail"] == "resume_already_in_progress"
        assert len(await _staged(rig, project_id)) == 1


# Scenario: A retry sent with the version read before an auto-reject is refused
@requires_postgres
@pytest.mark.asyncio
async def test_a_stale_website_retry_is_refused() -> None:
    async with _app() as rig:
        project_id, read_at = await _rejected(rig)

        status_code, body = await _retry(rig, project_id, read_at)

        assert status_code == 409
        assert body["detail"] == "version_conflict"
        assert await _staged(rig, project_id) == []
        row = await _row(rig, project_id)
        assert (row.phase_status, row.lock_version) == ("rejected", read_at + 1)


# Scenario: A tap from someone who does not own the carousel changes nothing
@requires_postgres
@pytest.mark.asyncio
async def test_an_admin_who_does_not_own_the_carousel_is_refused() -> None:
    async with _app() as rig:
        project_id, read_at = await _rejected(rig)
        admin = await create_test_user("admin@ae0606.test", UserRole.ADMIN)

        response = await rig.client.post(
            _path(project_id),
            json={"expected_version": read_at + 1},
            headers=auth_headers_for(admin),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "not_owner"
        assert await _staged(rig, project_id) == []


@requires_postgres
@pytest.mark.asyncio
async def test_a_missing_carousel_answers_not_found() -> None:
    async with _app() as rig:
        missing = str(uuid4())

        posted = await rig.client.post(_path(missing), json={"expected_version": 1})
        read = await rig.client.get(_path(missing))

        assert posted.status_code == 404
        assert read.status_code == 404
