"""Drive the one QA carousel of the production queue validation.

Runs inside the production backend container, with the app's own settings
(``docker exec -i <backend> python - <command> [project id] < prod_qa_run.py``).
It acts as the owner through the public dashboard API on the container's own
port, with an access token minted in memory from the app settings and never
printed. Only the QA project is ever touched: every command that changes
anything checks that the project's topic carries the QA marker first.

Commands (each prints one JSON line):
    preflight          active generation runs and QA projects already present
    start <date>       create the QA carousel and run its first phases (dashboard path)
    step <project>     approve the next gate unless it is the final review; report state
    verify <project>   duplicate images and builds, generation run attempts, stuck state
    cleanup <project>  cancel its queued runs, wait for its phase, delete it and its rows
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from collections.abc import Sequence

import httpx
from sqlalchemy import text

from rag_backend.infrastructure.auth import create_access_token
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import attach_db, get_session_maker
from rag_backend.infrastructure.database.models.user import UserModel

API = "http://127.0.0.1:8000/api"
QA_MARKER = "[QA "
QA_TOPIC = "[QA {date}] queue validation: filas de trabalho deixam sites rápidos"
QA_AUDIENCE = "devs"
QA_NICHE = "ai"
QA_BRIEF = (
    "Validação da fila de geração: por que tirar trabalho pesado do servidor web "
    "mantém o site rápido, com exemplos simples."
)
PERSONA_NAME = "Pedro"
START_TIMEOUT_SECONDS = 1200
REQUEST_TIMEOUT_SECONDS = 60
CLEANUP_WAIT_SECONDS = 1200
CLEANUP_POLL_SECONDS = 15
FINAL_PHASE = "final_review"
AWAITING = "awaiting_human"
IN_PROGRESS = "in_progress"
APPROVE = "approve"
ACTIVE = ("queued", "running", "retry_wait")

OTHER_ACTIVE_SQL = text(
    "SELECT count(*) FROM generation_runs WHERE status IN ('queued', 'running', 'retry_wait')"
    " AND coalesce(carousel_project_id, '') <> :project"
)
QA_PROJECTS_SQL = text(
    "SELECT id FROM carousel_projects WHERE topic LIKE '[QA %] queue validation%'"
)
TOPIC_SQL = text("SELECT topic, phase_status FROM carousel_projects WHERE id = :project")
PERSONA_SQL = text("SELECT id FROM persona_profiles WHERE name = :name LIMIT 1")
RUNS_SQL = text(
    "SELECT dedupe_key, status, attempts, phase_attempts::text, coalesce(last_phase, ''),"
    " coalesce(last_error_code, '') FROM generation_runs"
    " WHERE carousel_project_id = :project ORDER BY created_at"
)
DUPLICATE_IMAGES_SQL = text(
    "SELECT count(*) FROM (SELECT slide_number, prompt_hash FROM carousel_image_generations"
    " WHERE project_id = :project AND status = 'completed'"
    " GROUP BY slide_number, prompt_hash HAVING count(*) > 1) d"
)
IMAGES_SQL = text(
    "SELECT status, count(*) FROM carousel_image_generations WHERE project_id = :project"
    " GROUP BY status"
)
DUPLICATE_BUILDS_SQL = text(
    "SELECT count(*) FROM (SELECT artifact_version FROM carousel_artifact_builds"
    " WHERE project_id = :project GROUP BY artifact_version HAVING count(*) > 1) d"
)
CANCEL_SQL = text(
    "UPDATE generation_runs SET status = 'cancelled', finished_at = now(), updated_at = now()"
    " WHERE carousel_project_id = :project AND status IN ('queued', 'retry_wait')"
    " RETURNING pgq_job_id"
)
DROP_JOBS_SQL = text(
    "DELETE FROM pgqueuer WHERE id = ANY(:jobs) AND status = 'queued'"
)
LEFTOVER_COLUMNS = {
    "generation_runs": "carousel_project_id",
    "carousel_image_generations": "project_id",
    "carousel_artifact_builds": "project_id",
}
PURGE_COLUMNS = {
    **LEFTOVER_COLUMNS,
    "checkpoint_writes": "thread_id",
    "checkpoint_blobs": "thread_id",
    "checkpoints": "thread_id",
}


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, default=str))


async def _scalar(sql: object, **params: object) -> object:
    async with get_session_maker()() as session:
        return await session.scalar(sql, params)


async def _rows(sql: object, **params: object) -> list[list[object]]:
    async with get_session_maker()() as session:
        result = await session.execute(sql, params)
        return [list(row) for row in result.all()]


async def _token() -> str:
    settings = get_settings()
    async with get_session_maker()() as session:
        owner = await session.get(UserModel, settings.autopilot_owner_user_id)
    if owner is None:
        raise SystemExit("owner user not found")
    return create_access_token(settings, owner.to_entity())


async def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=API,
        headers={"Authorization": f"Bearer {await _token()}"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


async def _require_qa(project: str) -> str:
    row = await _rows(TOPIC_SQL, project=project)
    if not row or not str(row[0][0]).startswith(QA_MARKER):
        raise SystemExit("refusing: not the QA project")
    return str(row[0][1])


async def preflight() -> None:
    """How many other runs are active and which QA projects already exist."""
    _emit(
        {
            "other_active_runs": await _scalar(OTHER_ACTIVE_SQL, project=""),
            "qa_projects": [row[0] for row in await _rows(QA_PROJECTS_SQL)],
        }
    )


async def start(date: str) -> None:
    """Create the QA carousel as the owner and run its first phases."""
    topic = QA_TOPIC.format(date=date)
    persona = await _scalar(PERSONA_SQL, name=PERSONA_NAME)
    async with await _client() as client:
        created = await client.post(
            "/carousels",
            json={"topic": topic, "audience": QA_AUDIENCE, "niche": QA_NICHE, "persona_id": persona},
        )
        created.raise_for_status()
        project = str(created.json()["id"])
        _emit({"project_id": project, "created": True})
        started = await client.post(
            f"/carousels/{project}/workflow/start",
            json={"topic": topic, "audience": QA_AUDIENCE, "brief": QA_BRIEF, "persona_id": persona},
            timeout=START_TIMEOUT_SECONDS,
        )
    _emit({"project_id": project, "start_status": started.status_code})


async def _state(client: httpx.AsyncClient, project: str) -> dict[str, object]:
    response = await client.get(f"/carousels/{project}/workflow/state")
    response.raise_for_status()
    body: dict[str, object] = response.json()
    return body


async def step(project: str) -> None:
    """Approve the next gate (never the final review) and report where the run is."""
    await _require_qa(project)
    async with await _client() as client:
        state = await _state(client, project)
        phase, status = state.get("current_phase"), state.get("phase_status")
        approved = False
        if status == AWAITING and phase != FINAL_PHASE:
            response = await client.post(
                f"/carousels/{project}/workflow/resume",
                json={"action": APPROVE, "expected_version": state.get("lock_version")},
            )
            approved = response.status_code == httpx.codes.ACCEPTED
    _emit(
        {
            "phase": phase,
            "phase_status": status,
            "approved": approved,
            "done": status == AWAITING and phase == FINAL_PHASE,
            "runs": await _rows(RUNS_SQL, project=project),
            "other_active_runs": await _scalar(OTHER_ACTIVE_SQL, project=project),
        }
    )


async def verify(project: str) -> None:
    """Duplicates, attempts and whether anything is stuck."""
    status = await _require_qa(project)
    runs = await _rows(RUNS_SQL, project=project)
    _emit(
        {
            "phase_status": status,
            "runs": runs,
            "active_runs": sum(1 for run in runs if run[1] in ACTIVE),
            "images": await _rows(IMAGES_SQL, project=project),
            "duplicate_images": await _scalar(DUPLICATE_IMAGES_SQL, project=project),
            "duplicate_builds": await _scalar(DUPLICATE_BUILDS_SQL, project=project),
        }
    )


async def _leftovers(project: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    async with get_session_maker()() as session:
        for table, column in LEFTOVER_COLUMNS.items():
            counts[table] = int(
                await session.scalar(
                    text(f"SELECT count(*) FROM {table} WHERE {column} = :project"),
                    {"project": project},
                )
                or 0
            )
    return counts


async def _purge(project: str) -> None:
    async with get_session_maker()() as session:
        for table, column in PURGE_COLUMNS.items():
            exists = await session.scalar(text("SELECT to_regclass(:t)"), {"t": table})
            if exists is None:
                continue
            await session.execute(
                text(f"DELETE FROM {table} WHERE {column} = :project"), {"project": project}
            )
        await session.commit()


async def cleanup(project: str) -> None:
    """Cancel queued runs, wait for a running phase, delete the project and its rows."""
    await _require_qa(project)
    async with get_session_maker()() as session:
        jobs = [row[0] for row in (await session.execute(CANCEL_SQL, {"project": project})).all() if row[0]]
        if jobs:
            await session.execute(DROP_JOBS_SQL, {"jobs": jobs})
        await session.commit()
    deadline = time.monotonic() + CLEANUP_WAIT_SECONDS
    while time.monotonic() < deadline and await _require_qa(project) == IN_PROGRESS:
        await asyncio.sleep(CLEANUP_POLL_SECONDS)
    async with await _client() as client:
        deleted = await client.delete(f"/carousels/{project}")
    before = await _leftovers(project)
    await _purge(project)
    _emit(
        {
            "deleted_status": deleted.status_code,
            "leftovers_before_purge": before,
            "leftovers_after_purge": await _leftovers(project),
        }
    )


COMMANDS = {"step": step, "verify": verify, "cleanup": cleanup, "start": start}


async def main(argv: Sequence[str]) -> None:
    """Dispatch one command."""
    attach_db(get_settings().database_url)
    if argv[:1] == ["preflight"]:
        await preflight()
        return
    if len(argv) != 2 or argv[0] not in COMMANDS:
        raise SystemExit(__doc__)
    await COMMANDS[argv[0]](argv[1])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
