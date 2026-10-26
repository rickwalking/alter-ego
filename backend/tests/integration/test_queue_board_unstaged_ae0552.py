"""Unstaged autopilot rows appear once with safe display and recovery actions."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from httpx import AsyncClient

from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.modules.autopilot.domain.queue_position import position_of
from rag_backend.modules.autopilot.infrastructure.queue_control import SqlQueueControl
from rag_backend.modules.generation_queue.domain.models import GenerationStatus
from tests.integration.manual_reprocess_support import autopilot_run_row, project_row
from tests.integration.queue_board_ae0552_support import (
    BOARD,
    NOW,
    save_generation,
    save_rows,
    seed_autopilot,
)
from tests.integration.test_queue_board_api_ae0526 import _admin


async def test_unstaged_rows_are_display_only_and_generation_rows_win_dedupe(
    client: AsyncClient,
) -> None:
    """Scenario: Unstaged autopilot work appears immediately and only once"""
    unstaged = await seed_autopilot("queued", None, "Generate now")
    staged = await seed_autopilot("queued", None, "Already staged")
    generation = autopilot_run_row(staged, GenerationStatus.QUEUED)
    await save_generation(generation)
    async with get_session_maker()() as session:
        snapshot = await SqlQueueControl(session).snapshot()
    response = await client.get(BOARD, headers=await _admin())
    assert response.status_code == 200
    active = response.json()["active"]
    synthetic = _one(active, unstaged)
    staged_row = _one(active, staged)
    _assert_projectless(synthetic, unstaged)
    _assert_staged(staged_row, str(generation.id))
    telegram = position_of(snapshot, unstaged, NOW)
    assert telegram is not None
    assert synthetic["position"] == telegram.position


async def test_project_orphan_has_a_working_reprocess_target_and_then_dedupes(
    client: AsyncClient,
) -> None:
    """Scenario: A generating orphan has a safe project recovery target"""
    headers = await _admin()
    project_id = str(uuid4())
    autopilot_id = await seed_autopilot("generating", project_id, "Orphan")
    project = project_row(
        project_id, updated_at=NOW - timedelta(minutes=15), lock_version=4
    )
    await save_rows([project])
    before = await client.get(BOARD, headers=headers)
    orphan = _one(before.json()["active"], autopilot_id)
    _assert_orphan(orphan, project_id)
    accepted_id = await _reprocess(client, headers, project_id)
    after = await client.get(BOARD, headers=headers)
    staged = _one(after.json()["active"], autopilot_id)
    assert staged["id"] == accepted_id
    assert (staged["staged"], staged["priority"]) == (True, 1)
    assert staged["stuck_kind"] == "orphan"


async def _reprocess(
    client: AsyncClient, headers: dict[str, str], project_id: str
) -> str:
    response = await client.post(
        f"/api/carousels/{project_id}/workflow/reprocess",
        headers=headers,
        json={"expected_version": 4, "run_id": None},
    )
    assert response.status_code == 202
    return str(response.json()["run_id"])


def _assert_staged(row: dict[str, object], generation_id: str) -> None:
    assert row["staged"] is True
    assert row["id"] == generation_id
    assert row["can_cancel"] is True


def _one(rows: list[dict[str, object]], autopilot_id: object) -> dict[str, object]:
    matches = [row for row in rows if row["autopilot_run_id"] == str(autopilot_id)]
    assert len(matches) == 1
    return matches[0]


def _assert_projectless(row: dict[str, object], autopilot_id: object) -> None:
    assert row["id"] == str(autopilot_id)
    assert (row["staged"], row["priority"], row["project_id"]) == (False, 0, None)
    assert row["can_reprocess"] is False
    assert row["refusal_code"] == "projectless_unstaged"
    assert row["stuck_kind"] is None
    actions = (row["can_retry"], row["can_discard"], row["can_cancel"])
    assert actions == (False, False, False)
    assert row["run_heartbeat_at"] is None


def _assert_orphan(row: dict[str, object], project_id: str) -> None:
    assert (row["staged"], row["project_id"], row["phase"]) == (
        False,
        project_id,
        "content",
    )
    assert row["can_reprocess"] is True
    assert row["refusal_code"] is None
    assert (row["stuck_kind"], row["lock_version"]) == ("orphan", 4)
    assert row["run_heartbeat_at"] is None
    actions = (row["can_retry"], row["can_discard"], row["can_cancel"])
    assert actions == (False, False, False)
