"""Running-only liveness is read from the attributed carousel project."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from httpx import AsyncClient

from rag_backend.modules.generation_queue.domain.models import GenerationStatus
from tests.integration.manual_reprocess_support import autopilot_run_row, project_row
from tests.integration.queue_board_ae0552_support import (
    BOARD,
    NOW,
    at,
    save_rows,
    seed_autopilot,
)
from tests.integration.test_queue_board_api_ae0526 import _admin

_ITEM_KEYS = {
    "id",
    "kind",
    "status",
    "title",
    "project_id",
    "phase",
    "position",
    "eta",
    "started_at",
    "next_attempt_at",
    "run_heartbeat_at",
    "lock_version",
    "error_code",
    "staged",
    "autopilot_run_id",
    "priority",
    "can_reprocess",
    "refusal_code",
    "stuck_kind",
    "can_retry",
    "can_discard",
    "can_cancel",
}


@dataclass(frozen=True, kw_only=True)
class _LivenessData:
    first_project: str
    second_project: str
    running_id: UUID
    queued_id: UUID
    heartbeat: datetime
    started: datetime
    wrong_update: datetime


async def test_running_heartbeat_is_attributed_and_queued_rows_are_not_live(
    client: AsyncClient,
) -> None:
    """Scenario: Running liveness is attributed only to the current project attempt"""
    data = await _liveness_data()
    await _seed(data)
    response = await client.get(BOARD, headers=await _admin())
    assert response.status_code == 200
    items = {row["autopilot_run_id"]: row for row in response.json()["active"]}
    _assert_running(items[str(data.running_id)], data)
    _assert_queued(items[str(data.queued_id)])
    assert set(items[str(data.running_id)]) == _ITEM_KEYS
    assert "raw provider prompt" not in response.text


async def test_forbidden_board_access(client: AsyncClient) -> None:
    """Scenario: Polling stops on forbidden and running rows show liveness"""
    response = await client.get(BOARD)
    assert response.status_code == 403


async def _liveness_data() -> _LivenessData:
    first_project, second_project = str(uuid4()), str(uuid4())
    running_id = await seed_autopilot("generating", first_project, "Running")
    queued_id = await seed_autopilot("queued", second_project, "Queued")
    return _LivenessData(
        first_project=first_project,
        second_project=second_project,
        running_id=running_id,
        queued_id=queued_id,
        heartbeat=NOW - timedelta(seconds=30),
        started=NOW - timedelta(minutes=4),
        wrong_update=NOW - timedelta(hours=3),
    )


async def _seed(data: _LivenessData) -> None:
    await _seed_projects(data)
    await _seed_generations(data)


async def _seed_projects(data: _LivenessData) -> None:
    first = project_row(
        data.first_project,
        run_heartbeat_at=data.heartbeat,
        updated_at=data.wrong_update,
        lock_version=7,
    )
    second = project_row(data.second_project, run_heartbeat_at=NOW, lock_version=9)
    await save_rows([first, second])


async def _seed_generations(data: _LivenessData) -> None:
    running = autopilot_run_row(
        data.running_id,
        GenerationStatus.RUNNING,
        carousel_project_id=data.first_project,
        payload={"autopilot_run_id": str(data.running_id), "manual_priority": 1},
        started_at=data.started,
        updated_at=data.wrong_update,
        last_error="raw provider prompt",
    )
    queued = autopilot_run_row(
        data.queued_id,
        GenerationStatus.QUEUED,
        carousel_project_id=data.second_project,
        started_at=None,
    )
    await save_rows([running, queued])


def _assert_queued(row: dict[str, object]) -> None:
    assert row["run_heartbeat_at"] is None
    assert row["started_at"] is None
    assert (row["lock_version"], row["priority"]) == (9, 0)
    assert row["refusal_code"] == "normal_queued"


def _assert_running(row: dict[str, object], data: _LivenessData) -> None:
    assert row["project_id"] == data.first_project
    assert row["autopilot_run_id"] == str(data.running_id)
    assert at(str(row["started_at"])) == data.started
    assert at(str(row["run_heartbeat_at"])) == data.heartbeat
    assert (row["lock_version"], row["priority"], row["staged"]) == (7, 1, True)
    assert row["can_reprocess"] is False
    assert row["refusal_code"] == "fresh_running"
