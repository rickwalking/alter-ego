"""The dashboard's generation queue panel API, end to end on SQLite.

Feature: backend/tests/features/queue_board_api_ae0526.feature
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from httpx import AsyncClient

from rag_backend.domain.models import UserRole
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from tests.integration.conftest import auth_headers_for, create_test_user

_NOW = datetime.now(UTC).replace(microsecond=0)
_DEAD = "queue_dead_letter:run_budget_exhausted"
_BOARD = "/api/generation-runs"


async def _admin(email: str = "admin@queue.test") -> dict[str, str]:
    return auth_headers_for(await create_test_user(email, UserRole.ADMIN))


async def _topic(
    status: str = "promoted", title: str = "", age: timedelta = timedelta()
) -> UUID:
    topic_id = uuid4()
    async with get_session_maker()() as session:
        session.add(
            TopicCandidateModel(
                id=topic_id,
                title=title or f"Tema {topic_id.hex[:5]}",
                angle="a",
                why_viral="w",
                audience="a",
                niche="n",
                brief="b",
                sources=["https://example.com/a"],
                score=1,
                signal_hash=uuid4().hex,
                status=status,
                created_at=_NOW - age,
            )
        )
        await session.commit()
    return topic_id


async def _run(state: str, reason: str | None = None, title: str = "") -> UUID:
    topic_id = await _topic(title=title)
    run_id = uuid4()
    async with get_session_maker()() as session:
        session.add(
            AutopilotRunModel(
                id=run_id,
                topic_candidate_id=topic_id,
                state=state,
                state_reason=reason,
                publish_attempts=0,
                telegram_message_ids=[],
                created_at=_NOW - timedelta(hours=1),
                updated_at=_NOW - timedelta(hours=1),
            )
        )
        await session.commit()
    return run_id


async def _generation(
    status: str,
    autopilot_run_id: UUID | None,
    minutes_ago: int,
    kind: str = "autopilot_drive",
) -> UUID:
    run_id = uuid4()
    created = _NOW - timedelta(minutes=minutes_ago)
    async with get_session_maker()() as session:
        session.add(
            GenerationRunModel(
                id=run_id,
                kind=kind,
                dedupe_key=f"k:{run_id}",
                status=status,
                payload={"project_title": "Projeto do painel"},
                autopilot_run_id=str(autopilot_run_id) if autopilot_run_id else None,
                carousel_project_id="proj-1" if kind == "workflow_resume" else None,
                attempts=2,
                phase_attempts={"images": 2},
                last_phase="images",
                last_error_code="run_budget_exhausted"
                if status == "dead_letter"
                else None,
                created_at=created,
                started_at=created if status != "queued" else None,
                finished_at=created if status == "dead_letter" else None,
                updated_at=created,
            )
        )
        await session.commit()
    return run_id


async def _state(run_id: UUID) -> tuple[str, str | None]:
    async with get_session_maker()() as session:
        row = await session.get(AutopilotRunModel, run_id)
    assert row is not None
    return row.state, row.state_reason


async def _status(generation_id: UUID) -> str:
    async with get_session_maker()() as session:
        row = await session.get(GenerationRunModel, generation_id)
    assert row is not None
    return row.status


async def test_the_board_lists_active_runs_in_fifo_order(client: AsyncClient) -> None:
    """Scenario: The board lists the active runs in FIFO order with positions"""
    headers = await _admin()
    first = await _generation("queued", await _run("queued", title="Primeiro"), 30)
    running = await _generation(
        "running", await _run("generating", title="Rodando"), 40
    )
    second = await _generation("queued", await _run("queued", title="Segundo"), 10)
    response = await client.get(_BOARD, headers=headers)
    assert response.status_code == 200
    active = response.json()["active"]
    assert [item["id"] for item in active] == [str(running), str(first), str(second)]
    assert [item["position"] for item in active] == [1, 2, 3]
    assert active[0]["eta"] is None
    assert active[1]["eta"] is not None
    assert active[1]["title"] == "Primeiro"
    assert active[1]["can_cancel"] is True
    assert active[0]["can_cancel"] is False


async def test_parked_runs_are_listed_until_resolved(client: AsyncClient) -> None:
    """Scenario: A parked autopilot run is listed until it is resolved"""
    headers = await _admin()
    parked = await _generation("dead_letter", await _run("escalated", _DEAD), 20)
    await _generation("dead_letter", await _run("rejected", "owner_queue_discard"), 25)
    dead = (await client.get(_BOARD, headers=headers)).json()["dead"]
    assert [item["id"] for item in dead] == [str(parked)]
    assert dead[0]["can_retry"] is True
    assert dead[0]["can_discard"] is True
    assert dead[0]["error_code"] == "run_budget_exhausted"
    assert dead[0]["can_reprocess"] is True
    assert dead[0]["refusal_code"] is None
    assert dead[0]["stuck_kind"] == "dead_letter"
    assert dead[0]["staged"] is True


async def test_a_parked_dashboard_resume_has_no_buttons(client: AsyncClient) -> None:
    """Scenario: A parked dashboard resume is listed without buttons"""
    headers = await _admin()
    await _generation("dead_letter", None, 5, kind="workflow_resume")
    dead = (await client.get(_BOARD, headers=headers)).json()["dead"]
    assert len(dead) == 1
    await _generation("succeeded", None, 1, kind="workflow_resume")
    assert (await client.get(_BOARD, headers=headers)).json()["dead"] == []
    assert dead[0]["kind"] == "dashboard"
    assert dead[0]["project_id"] == "proj-1"
    assert dead[0]["title"] == "Projeto do painel"
    assert (dead[0]["can_retry"], dead[0]["can_discard"], dead[0]["can_cancel"]) == (
        False,
        False,
        False,
    )


async def test_the_backlog_is_listed_with_its_expiry(client: AsyncClient) -> None:
    """Scenario: The backlog is listed with the day each theme expires"""
    headers = await _admin()
    theme = await _topic("backlog_noted", "Tema em espera", timedelta(days=2))
    backlog = (await client.get(_BOARD, headers=headers)).json()["backlog"]
    assert [item["candidate_id"] for item in backlog] == [str(theme)]
    created = datetime.fromisoformat(backlog[0]["created_at"])
    expires = datetime.fromisoformat(backlog[0]["expires_at"])
    assert expires - created == timedelta(days=7)


async def test_retry_from_the_panel_happens_once(client: AsyncClient) -> None:
    """Scenario: Retry from the panel puts the run back in the queue once"""
    headers = await _admin()
    run = await _run("escalated", _DEAD)
    dead = await _generation("dead_letter", run, 20)
    first = await client.post(f"{_BOARD}/{dead}/retry", headers=headers)
    second = await client.post(f"{_BOARD}/{dead}/retry", headers=headers)
    assert first.status_code == 200
    assert first.json() == {"outcome": "done"}
    assert second.status_code == 409
    assert second.json()["detail"] == "already_resolved"
    assert await _state(run) == ("generating", "owner_queue_retry")
    assert await _status(dead) == "queued"
    async with get_session_maker()() as session:
        row = await session.get(GenerationRunModel, dead)
    assert row is not None
    assert row.payload["manual_priority"] == 1
    assert row.payload["manual_origin"] == "carousel_reprocess"


async def test_discard_from_the_panel_closes_the_run(client: AsyncClient) -> None:
    """Scenario: Discard from the panel closes the run"""
    headers = await _admin()
    run = await _run("escalated", _DEAD)
    dead = await _generation("dead_letter", run, 20)
    response = await client.post(f"{_BOARD}/{dead}/discard", headers=headers)
    assert response.status_code == 200
    assert await _state(run) == ("rejected", "owner_queue_discard")


async def test_cancel_takes_a_run_that_has_not_started_out(client: AsyncClient) -> None:
    """Scenario: Cancel takes a run that has not started out of the queue"""
    headers = await _admin()
    run = await _run("queued")
    queued = await _generation("queued", run, 5)
    response = await client.post(f"{_BOARD}/{queued}/cancel", headers=headers)
    assert response.status_code == 200
    assert await _status(queued) == "cancelled"
    assert await _state(run) == ("failed", "owner_queue_cancelled")


async def test_cancel_is_refused_for_running_and_dashboard_work(
    client: AsyncClient,
) -> None:
    """Scenario: Cancel is refused for a running drive or a dashboard resume"""
    headers = await _admin()
    running = await _generation("running", await _run("generating"), 5)
    resume = await _generation("queued", None, 3, kind="workflow_resume")
    started = await _generation("queued", await _run("generating"), 2)
    for generation_id in (running, resume, started):
        response = await client.post(
            f"{_BOARD}/{generation_id}/cancel", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "not_allowed"
    assert await _status(running) == "running"
    assert await _status(resume) == "queued"
    assert await _status(started) == "queued"


async def test_generate_now_from_the_panel_happens_once(client: AsyncClient) -> None:
    """Scenario: Gerar agora from the panel queues a backlog theme once"""
    headers = await _admin()
    theme = await _topic("backlog_noted", "Agora", timedelta(days=1))
    path = f"/api/generation-runs/backlog/{theme}/generate"
    first = await client.post(path, headers=headers)
    second = await client.post(path, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 409
    async with get_session_maker()() as session:
        runs = await session.execute(
            AutopilotRunModel.__table__.select().where(
                AutopilotRunModel.topic_candidate_id == theme
            )
        )
        assert len(runs.all()) == 1


async def test_an_unknown_run_answers_404(client: AsyncClient) -> None:
    """Scenario: An unknown run answers 404"""
    headers = await _admin()
    response = await client.post(f"{_BOARD}/{uuid4()}/retry", headers=headers)
    assert response.status_code == 404
    theme = await client.post(f"{_BOARD}/backlog/{uuid4()}/generate", headers=headers)
    assert theme.status_code == 404


async def test_an_expired_theme_cannot_be_generated(client: AsyncClient) -> None:
    """Scenario: Gerar agora from the panel queues a backlog theme once"""
    headers = await _admin()
    theme = await _topic("backlog_noted", "Vencido", timedelta(days=8))
    response = await client.post(f"{_BOARD}/backlog/{theme}/generate", headers=headers)
    assert response.status_code == 409
    board = (await client.get(_BOARD, headers=headers)).json()
    assert board["backlog"] == []


async def test_cancel_is_not_offered_for_a_run_already_generating(
    client: AsyncClient,
) -> None:
    """Scenario: Cancel is refused for a running drive or a dashboard resume"""
    headers = await _admin()
    await _generation("retry_wait", await _run("generating"), 6)
    active = (await client.get(_BOARD, headers=headers)).json()["active"]
    assert active[0]["can_cancel"] is False
    assert active[0]["position"] is None
    assert active[0]["can_reprocess"] is True
    assert active[0]["stuck_kind"] == "retry_wait"
    assert active[0]["run_heartbeat_at"] is None


async def test_the_panel_api_is_admin_only(client: AsyncClient) -> None:
    """Scenario: The panel API is admin only"""
    target = uuid4()
    calls = [
        client.get(_BOARD),
        client.post(f"{_BOARD}/{target}/retry"),
        client.post(f"{_BOARD}/{target}/discard"),
        client.post(f"{_BOARD}/{target}/cancel"),
        client.post(f"/api/generation-runs/backlog/{target}/generate"),
    ]
    for call in calls:
        response = await call
        assert response.status_code == 403
