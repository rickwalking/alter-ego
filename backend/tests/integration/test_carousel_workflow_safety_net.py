"""Carousel editorial workflow byte-identical safety-net tests (AE-0106).

Behavioral + golden-snapshot safety net for the Phase 4 carousel WORKFLOW
extraction. Every behavior test asserts the /api workflow contract that the
relocation (AE-0107 / AE-0110 / AE-0111 — workflow start/state/resume + the
``carousel_projects`` writers behind editorial handlers + an ACL) must preserve.

The golden snapshots capture the deterministic baseline of GET ``workflow/state``,
POST ``workflow/start`` and POST ``workflow/resume`` INCLUDING the artifact URL
fields the state response exposes (``image_assets`` image paths,
``blog_markdown``, ``design_applied``). Volatile fields (the workflow
``project_id`` UUID, timestamps) are normalized via the diff helper.

The SSE stream test uses a DETERMINISTIC stub workflow service (fixed event
sequence) and asserts event TYPES in order + ``id:``/``event:``/``data:``
framing + keep-alive interleaving is ignored + the current Last-Event-ID
contract (this stream does NOT implement resume, so ids always start at 1). It
is FALSIFIABLE: a reordered or renamed event changes the asserted list. It never
byte-diffs live LLM/phase content.

The seam mirrors AE-0097 (which patched ``chat_stream.build_alter_ego_agent``):
the route module ``editorial_workflow`` imports ``build_editorial_workflow_service``
at module level and calls it for every endpoint, so we monkeypatch THAT
module-level name with a deterministic stub. No production code is modified.

Feature file: tests/features/carousel_editorial_workflow_safety_net.feature

Run with ``--snapshot-update`` (flag registered in tests/conftest.py) to
regenerate the committed golden snapshots from current, pre-refactor behavior.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator, AsyncIterator
from typing import TYPE_CHECKING, Final
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from rag_backend.application.services.carousel.editorial_workflow_sse_build import (
    EventParams,
    build_artifact_event,
    build_phase_change_event,
    build_progress_event,
    build_review_gate_payload,
    build_review_required_event,
)
from rag_backend.application.services.carousel.editorial_workflow_sse_constants import (
    SSE_EVENT_ARTIFACT,
    SSE_EVENT_KEEPALIVE,
    SSE_EVENT_PHASE_CHANGE,
    SSE_EVENT_PROGRESS,
    SSE_EVENT_REVIEW_REQUIRED,
    SSE_PAYLOAD_FIELD_EVENT,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models import User, UserRole
from tests.integration.conftest import TEST_SECRET, auth_headers_for, create_test_user
from tests.snapshots.editorial import _snapshot as editorial_snapshot

if TYPE_CHECKING:
    from fastapi import FastAPI
    from httpx import Response
    from sqlalchemy.ext.asyncio import AsyncEngine

# --- Constants -----------------------------------------------------------------
SNAPSHOT_UPDATE_OPTION = "--snapshot-update"
ANON_SECRET = "test-anon-secret-for-integration-tests"
EDITOR_EMAIL = "wf-editor@integration.example.com"
OTHER_EDITOR_EMAIL = "wf-other@integration.example.com"

# Deterministic, STABLE artifact paths (no embedded volatile UUID) so the state
# snapshot captures the artifact URL fields byte-for-byte (AC: artifact URLs).
ARTIFACT_IMAGE_1 = "/media/carousel/fixture/slide-1.png"
ARTIFACT_IMAGE_2 = "/media/carousel/fixture/slide-2.png"
ARTIFACT_BLOG_MARKDOWN = "# Fixture blog\n\nDeterministic blog body for the snapshot."
ARTIFACT_CAPTION = "Fixture caption for the snapshot."

# Deterministic SSE phase-progress payload for the stream fixture.
FIXTURE_PHASE_PROGRESS: Final[dict[str, object]] = {"percent": 42, "step": "drafting"}

# SSE event types that the workflow stream may emit (allowlist for assertions).
WORKFLOW_SSE_EVENT_TYPES: Final[tuple[str, ...]] = (
    SSE_EVENT_PHASE_CHANGE,
    SSE_EVENT_PROGRESS,
    SSE_EVENT_REVIEW_REQUIRED,
    SSE_EVENT_ARTIFACT,
)


@pytest.fixture
def snapshot_update(request: pytest.FixtureRequest) -> bool:
    """Whether snapshots should be written instead of asserted."""
    return bool(request.config.getoption(SNAPSHOT_UPDATE_OPTION))


# --- Engine / app factory ------------------------------------------------------
async def _make_engine(db_path: str) -> AsyncEngine:
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.infrastructure.database.config import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    return engine


def _fixture_state(project_id: str) -> CarouselWorkflowState:
    """Deterministic mid-workflow state INCLUDING artifact URL fields.

    The state response surfaces artifact URLs via ``image_assets`` (image
    paths), ``blog_markdown`` (blog artifact) and ``design_applied`` (design).
    Paths are stable (no volatile UUID) so they snapshot byte-identically.
    """
    state: CarouselWorkflowState = {
        "project_id": project_id,
        "current_phase": PHASE_CONTENT,
        "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        "research_findings": [{"finding": "fixture finding"}],
        # NOTE: ``slide_drafts`` / ``outline`` are intentionally omitted. The
        # state-response builder re-derives ``presentation_validation`` /
        # ``localized_slides`` from drafts using a LIVE ``validated_at`` timestamp
        # (``datetime.now``), which is non-deterministic and would defeat the
        # byte-identical baseline. With no drafts, nothing volatile is derived
        # (presentation_validation -> None) and the approve gate is non-blocking.
        "image_assets": [ARTIFACT_IMAGE_1, ARTIFACT_IMAGE_2],
        "design_applied": True,
        "phase_progress": dict(FIXTURE_PHASE_PROGRESS),
        "status": "draft",
        "workflow_status": "running",
        "persona_scores": {"slide-0": {"overall": 88}},
        "caption": ARTIFACT_CAPTION,
        "blog_markdown": ARTIFACT_BLOG_MARKDOWN,
        "rubric_scores": {"clarity": 9},
        "phase_feedback": {"content": ["looks good"]},
        "revision_count": {"content": 1},
    }
    return state


class _StubWorkflowService:
    """Deterministic stand-in for EditorialWorkflowService.

    Implements only the methods the route handlers call, with fixed return
    values. Never constructs a real LLM / Pinecone / orchestrator client, so the
    tests are key-free and byte-deterministic. The SSE event sequence is fixed,
    making the stream falsifiable by a reordered or renamed event.
    """

    def __init__(self, project_id: str, *, has_state: bool) -> None:
        self._project_id = project_id
        self._has_state = has_state
        self._state = _fixture_state(project_id) if has_state else None

    async def get_workflow_state(
        self,
        project_id: str,
        db: object | None = None,
    ) -> CarouselWorkflowState | None:
        del db
        if not self._has_state or project_id != self._project_id:
            return None
        return dict(self._state) if self._state is not None else None

    async def start_workflow(
        self,
        project_id: str,
        workflow_input: object,
        db: object | None = None,
    ) -> CarouselWorkflowState:
        del workflow_input, db
        return _fixture_state(project_id)

    async def read_checkpoint_phase(self, project_id: str) -> str:
        del project_id
        return PHASE_CONTENT

    async def mark_resume_in_progress(
        self,
        project_id: str,
        db: object | None = None,
    ) -> str:
        del project_id, db
        return PHASE_CONTENT

    def stream_phase_updates(
        self,
        project_id: str,
        *,
        phase_progress: dict[str, object] | None = None,
    ) -> AsyncIterator[dict[str, object]]:
        del phase_progress
        return _fixed_sse_sequence(project_id, self._state)


async def _fixed_sse_sequence(
    project_id: str,
    state: CarouselWorkflowState | None,
) -> AsyncIterator[dict[str, object]]:
    """Yield a FIXED workflow event sequence with a keep-alive interleaved.

    Order: phase_change -> progress -> (keep-alive) -> artifact -> review_required.
    The keep-alive is dropped by the route (yields ``: keepalive``) and by the
    test parser, so its interleaving never affects the asserted event sequence.
    A reordered or renamed event changes the asserted type list -> falsifiable.
    """
    resolved_state = state if state is not None else _fixture_state(project_id)
    params = EventParams(project_id=project_id, phase=PHASE_CONTENT)
    yield build_phase_change_event(
        project_id, PHASE_CONTENT, PHASE_STATUS_AWAITING_HUMAN
    )
    yield build_progress_event(project_id, PHASE_CONTENT, dict(FIXTURE_PHASE_PROGRESS))
    yield {SSE_PAYLOAD_FIELD_EVENT: SSE_EVENT_KEEPALIVE}
    yield build_artifact_event(params, artifact_type="outline", data=[{"slide": 1}])
    yield build_review_required_event(
        params,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        gate_payload=build_review_gate_payload(resolved_state),
    )


class WfEnv:
    """Test environment: app + DB engine + seeding/client helpers."""

    def __init__(self, app: FastAPI, editor: User, other: User) -> None:
        self._app = app
        self.editor = editor
        self.other = other

    def client_for(self, user: User) -> AsyncClient:
        transport = ASGITransport(app=self._app)
        return AsyncClient(
            transport=transport,
            base_url="http://test",
            headers=auth_headers_for(user),
        )

    async def seed_project(self, owner: User, *, lock_version: int = 1) -> str:
        """Persist a carousel project owned by ``owner`` and return its id."""
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        project_id = str(uuid4())
        session_maker = get_session_maker()
        async with session_maker() as session:
            project = CarouselProjectModel(
                id=project_id,
                owner_id=str(owner.id),
                topic="Fixture topic",
                audience="Fixture audience",
                niche="Fixture niche",
                current_phase=PHASE_CONTENT,
                phase_status=PHASE_STATUS_AWAITING_HUMAN,
                lock_version=lock_version,
                phase_progress=dict(FIXTURE_PHASE_PROGRESS),
            )
            session.add(project)
            await session.commit()
        return project_id

    async def project_lock_version(self, project_id: str) -> int:
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        session_maker = get_session_maker()
        async with session_maker() as session:
            project = await session.get(CarouselProjectModel, project_id)
            assert project is not None
            return int(project.lock_version or 1)


@pytest_asyncio.fixture
async def wf_env(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[WfEnv, None]:
    """Shared file-backed DB + app with two editors and client helpers."""
    from pathlib import Path

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.database.config import close_db

    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = ANON_SECRET
    # Pin DEBUG so every env-sensitive setting (cookie ``secure`` etc.) is
    # deterministic local vs CI. This exact local(DEBUG=true)/CI(DEBUG=false)
    # split broke the Phase-3 safety net; pin it via monkeypatch.setenv +
    # settings cache clear (monkeypatch auto-reverts the env at test end).
    monkeypatch.setenv("DEBUG", "false")
    get_settings.cache_clear()

    assert isinstance(tmp_path, Path)
    db_path = str(tmp_path / "wf_env.db")
    engine = await _make_engine(db_path)
    editor = await create_test_user(EDITOR_EMAIL, UserRole.EDITOR)
    other = await create_test_user(OTHER_EDITOR_EMAIL, UserRole.EDITOR)
    app = create_app()
    env = WfEnv(app=app, editor=editor, other=other)
    try:
        yield env
    finally:
        db_config.c_engine = None
        await close_db()
        await engine.dispose()


def _patch_service(
    monkeypatch: pytest.MonkeyPatch,
    project_id: str,
    *,
    has_state: bool = True,
) -> _StubWorkflowService:
    """Replace the route's service builder with a deterministic stub.

    Mirrors AE-0097's ``build_alter_ego_agent`` patch: the route module imports
    ``build_editorial_workflow_service`` at module level and calls it per
    request, so patching that name injects the stub at the app edge.
    """
    from rag_backend.api.routes.carousels import editorial_workflow as wf_module

    stub = _StubWorkflowService(project_id, has_state=has_state)
    monkeypatch.setattr(
        wf_module, "build_editorial_workflow_service", lambda _request: stub
    )
    return stub


def _patch_no_background_resume(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the fire-and-forget background resume so no real workflow runs."""
    from rag_backend.api.routes.carousels import editorial_workflow as wf_module

    monkeypatch.setattr(
        wf_module, "schedule_background_resume", lambda _service, _params: None
    )


# --- SSE parsing helpers -------------------------------------------------------
def _parse_sse(text: str) -> list[tuple[int | None, str, dict[str, object]]]:
    """Parse raw SSE text into ``(id, event, data)`` triples.

    Keep-alive comments (lines starting with ``:``) are dropped so ping
    interleaving never affects the asserted event sequence.
    """
    events: list[tuple[int | None, str, dict[str, object]]] = []
    event_id: int | None = None
    event_type = ""
    data = ""
    for line in text.split("\n"):
        if line.startswith("id: "):
            event_id = int(line[4:])
        elif line.startswith("event: "):
            event_type = line[7:]
        elif line.startswith("data: "):
            data += line[6:]
        elif line == "":
            if data:
                events.append((event_id, event_type, json.loads(data)))
            event_id = None
            event_type = ""
            data = ""
    return events


def _event_types(events: list[tuple[int | None, str, dict[str, object]]]) -> list[str]:
    return [event_type for _id, event_type, _data in events]


# ==============================================================================
# GET /workflow/state behavior + snapshot
# ==============================================================================
class TestWorkflowStateBehavior:
    """GET workflow/state contract (tests/features/...safety_net.feature)."""

    @pytest.mark.asyncio
    async def test_state_returns_200_for_owner(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Workflow state response is unchanged for a mid-workflow project."""
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=True)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.get(f"/api/carousels/{project_id}/workflow/state")
        assert resp.status_code == 200
        body = resp.json()
        assert body["current_phase"] == PHASE_CONTENT
        # Artifact URL fields are surfaced (AC: include artifact URLs).
        assert body["image_assets"] == [ARTIFACT_IMAGE_1, ARTIFACT_IMAGE_2]
        assert body["blog_markdown"] == ARTIFACT_BLOG_MARKDOWN
        assert body["design_applied"] is True

    @pytest.mark.asyncio
    async def test_state_returns_404_when_no_checkpoint(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Workflow state returns 404 when no checkpoint exists."""
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=False)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.get(f"/api/carousels/{project_id}/workflow/state")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_state_forbidden_for_non_owner(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Workflow state is forbidden for a non-owner non-reviewer."""
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=True)
        async with wf_env.client_for(wf_env.other) as client:
            resp = await client.get(f"/api/carousels/{project_id}/workflow/state")
        assert resp.status_code == 403


# ==============================================================================
# POST /workflow/start behavior
# ==============================================================================
class TestWorkflowStartBehavior:
    """POST workflow/start contract."""

    @pytest.mark.asyncio
    async def test_start_returns_200(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Workflow start response is unchanged."""
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=False)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.post(
                f"/api/carousels/{project_id}/workflow/start",
                json={
                    "topic": "Fixture topic",
                    "audience": "Fixture audience",
                    "brief": "Fixture brief",
                    "sources": [],
                },
            )
        assert resp.status_code == 200
        assert resp.json()["current_phase"] == PHASE_CONTENT

    @pytest.mark.asyncio
    async def test_start_rejects_self_reviewer(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Workflow start rejects self-assignment as reviewer."""
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=False)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.post(
                f"/api/carousels/{project_id}/workflow/start",
                json={
                    "topic": "Fixture topic",
                    "audience": "Fixture audience",
                    "brief": "Fixture brief",
                    "sources": [],
                    "reviewer_id": str(wf_env.editor.id),
                },
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_start_synthesis_failure_is_logged_with_specific_detail(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Repair failure fails closed with an observable error
        (tests/features/source_synthesis_hardening.feature, AE-0318)."""
        import structlog

        from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
        from rag_backend.domain.constants.carousel_workflow import (
            ERR_RESEARCH_SYNTHESIS_FAILED,
        )

        project_id = await wf_env.seed_project(wf_env.editor)
        stub = _patch_service(monkeypatch, project_id, has_state=False)

        async def _raise_start(
            project_id: str,
            workflow_input: object,
            db: object | None = None,
        ) -> CarouselWorkflowState:
            del project_id, workflow_input, db
            raise ValueError(ERR_INVALID_JSON)

        monkeypatch.setattr(stub, "start_workflow", _raise_start)
        with structlog.testing.capture_logs() as logs:
            async with wf_env.client_for(wf_env.editor) as client:
                resp = await client.post(
                    f"/api/carousels/{project_id}/workflow/start",
                    json={
                        "topic": "Fixture topic",
                        "audience": "Fixture audience",
                        "brief": "Fixture brief",
                        "sources": [],
                    },
                )
        assert resp.status_code == 400
        assert resp.json()["detail"] == ERR_RESEARCH_SYNTHESIS_FAILED
        failures = [log for log in logs if log["event"] == "workflow_start_failed"]
        assert failures
        assert failures[0]["project_id"] == project_id
        assert failures[0]["error"] == ERR_INVALID_JSON

    @pytest.mark.asyncio
    async def test_start_non_synthesis_value_error_keeps_generic_detail(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Repair failure fails closed (scoping half, AE-0318 r1 M1):
        a non-synthesis ValueError must NOT be labeled research_synthesis_failed."""
        import structlog

        from rag_backend.domain.constants.access_control import ERR_INVALID_REQUEST

        project_id = await wf_env.seed_project(wf_env.editor)
        stub = _patch_service(monkeypatch, project_id, has_state=False)

        async def _raise_start(
            project_id: str,
            workflow_input: object,
            db: object | None = None,
        ) -> CarouselWorkflowState:
            del project_id, workflow_input, db
            raise ValueError("some_other_engine_error")

        monkeypatch.setattr(stub, "start_workflow", _raise_start)
        with structlog.testing.capture_logs() as logs:
            async with wf_env.client_for(wf_env.editor) as client:
                resp = await client.post(
                    f"/api/carousels/{project_id}/workflow/start",
                    json={
                        "topic": "Fixture topic",
                        "audience": "Fixture audience",
                        "brief": "Fixture brief",
                        "sources": [],
                    },
                )
        assert resp.status_code == 400
        assert resp.json()["detail"] == ERR_INVALID_REQUEST
        failures = [log for log in logs if log["event"] == "workflow_start_failed"]
        assert failures and failures[0]["error"] == "some_other_engine_error"

    @pytest.mark.asyncio
    async def test_start_provider_rate_limit_maps_to_429(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Provider rate limit maps to 429
        (tests/features/workflow_start_provider_errors.feature, AE-0319)."""
        import httpx
        import openai
        import structlog

        from rag_backend.domain.constants.carousel_workflow import (
            ERR_PROVIDER_RATE_LIMITED,
        )

        project_id = await wf_env.seed_project(wf_env.editor)
        stub = _patch_service(monkeypatch, project_id, has_state=False)

        async def _raise_start(
            project_id: str,
            workflow_input: object,
            db: object | None = None,
        ) -> CarouselWorkflowState:
            del project_id, workflow_input, db
            request = httpx.Request("POST", "https://provider.example.com/v1/chat")
            response = httpx.Response(429, request=request, json={"error": {}})
            raise openai.RateLimitError(
                "usage limit reached", response=response, body=None
            )

        monkeypatch.setattr(stub, "start_workflow", _raise_start)
        with structlog.testing.capture_logs() as logs:
            async with wf_env.client_for(wf_env.editor) as client:
                resp = await client.post(
                    f"/api/carousels/{project_id}/workflow/start",
                    json={
                        "topic": "Fixture topic",
                        "audience": "Fixture audience",
                        "brief": "Fixture brief",
                        "sources": [],
                    },
                )
        assert resp.status_code == 429
        assert resp.json()["detail"] == ERR_PROVIDER_RATE_LIMITED
        errors = [
            log for log in logs if log["event"] == "workflow_start_provider_error"
        ]
        assert errors and errors[0]["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_start_provider_outage_maps_to_503(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Provider outage maps to 503 (AE-0319)."""
        import httpx
        import openai

        from rag_backend.domain.constants.carousel_workflow import (
            ERR_PROVIDER_UNAVAILABLE,
        )

        project_id = await wf_env.seed_project(wf_env.editor)
        stub = _patch_service(monkeypatch, project_id, has_state=False)

        async def _raise_start(
            project_id: str,
            workflow_input: object,
            db: object | None = None,
        ) -> CarouselWorkflowState:
            del project_id, workflow_input, db
            request = httpx.Request("POST", "https://provider.example.com/v1/chat")
            response = httpx.Response(502, request=request, json={"error": {}})
            raise openai.APIStatusError("bad gateway", response=response, body=None)

        monkeypatch.setattr(stub, "start_workflow", _raise_start)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.post(
                f"/api/carousels/{project_id}/workflow/start",
                json={
                    "topic": "Fixture topic",
                    "audience": "Fixture audience",
                    "brief": "Fixture brief",
                    "sources": [],
                },
            )
        assert resp.status_code == 503
        assert resp.json()["detail"] == ERR_PROVIDER_UNAVAILABLE


# ==============================================================================
# POST /workflow/resume behavior + interrupt->resume gates + optimistic lock
# ==============================================================================
class TestWorkflowResumeBehavior:
    """POST workflow/resume contract: gates + optimistic lock."""

    @pytest.mark.asyncio
    async def test_resume_approve_returns_202_and_bumps_version(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Workflow resume accepts an approve and returns 202."""
        project_id = await wf_env.seed_project(wf_env.editor, lock_version=1)
        _patch_service(monkeypatch, project_id, has_state=True)
        _patch_no_background_resume(monkeypatch)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.post(
                f"/api/carousels/{project_id}/workflow/resume",
                json={"action": "approve", "expected_version": 1},
            )
        assert resp.status_code == 202
        body = resp.json()
        assert body["accepted"] is True
        assert body["phase_status"] == PHASE_STATUS_IN_PROGRESS
        assert body["lock_version"] == 2
        assert await wf_env.project_lock_version(project_id) == 2

    @pytest.mark.asyncio
    async def test_resume_rejects_unsupported_action(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Workflow resume rejects an unsupported action."""
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=True)
        _patch_no_background_resume(monkeypatch)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.post(
                f"/api/carousels/{project_id}/workflow/resume",
                json={"action": "reject", "expected_version": 1},
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_resume_revise_requires_feedback(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Workflow resume requires feedback for a revise action."""
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=True)
        _patch_no_background_resume(monkeypatch)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.post(
                f"/api/carousels/{project_id}/workflow/resume",
                json={"action": "revise", "feedback": "   ", "expected_version": 1},
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_resume_stale_version_conflict(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Workflow resume rejects a stale expected version."""
        project_id = await wf_env.seed_project(wf_env.editor, lock_version=1)
        _patch_service(monkeypatch, project_id, has_state=True)
        _patch_no_background_resume(monkeypatch)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.post(
                f"/api/carousels/{project_id}/workflow/resume",
                json={"action": "approve", "expected_version": 99},
            )
        assert resp.status_code == 409
        assert resp.json()["detail"] == ERR_VERSION_CONFLICT

    @pytest.mark.asyncio
    async def test_concurrent_resume_optimistic_lock(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Concurrent resume — only the first bump wins."""
        project_id = await wf_env.seed_project(wf_env.editor, lock_version=1)
        _patch_service(monkeypatch, project_id, has_state=True)
        _patch_no_background_resume(monkeypatch)
        async with wf_env.client_for(wf_env.editor) as client:
            first = await client.post(
                f"/api/carousels/{project_id}/workflow/resume",
                json={"action": "approve", "expected_version": 1},
            )
            # The second request reuses the now-stale expected_version 1; the DB
            # row is at lock_version 2, so the optimistic-lock bump conflicts.
            second = await client.post(
                f"/api/carousels/{project_id}/workflow/resume",
                json={"action": "approve", "expected_version": 1},
            )
        assert first.status_code == 202
        # The first resume left the project in_progress; the second is rejected
        # before the version check (resume-already-in-progress) OR at the
        # version check — both deterministic 409s. Assert the conflict status.
        assert second.status_code == 409


# ==============================================================================
# GET /workflow/stream — deterministic SSE event-type ordering + framing
# ==============================================================================
class TestWorkflowStreamSse:
    """Deterministic SSE event-type ordering, framing, keep-alive, Last-Event-ID."""

    @pytest.mark.asyncio
    async def test_event_types_in_order(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Workflow stream emits the same SSE event sequence.

        Falsifiable: a reordered or renamed event changes this exact list.
        """
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=True)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.get(f"/api/carousels/{project_id}/workflow/stream")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        events = _parse_sse(resp.text)
        types = _event_types(events)
        assert types == [
            SSE_EVENT_PHASE_CHANGE,
            SSE_EVENT_PROGRESS,
            SSE_EVENT_ARTIFACT,
            SSE_EVENT_REVIEW_REQUIRED,
        ]
        for event_type in types:
            assert event_type in WORKFLOW_SSE_EVENT_TYPES

    @pytest.mark.asyncio
    async def test_reordered_event_is_falsifiable(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: stream is falsifiable by a reordered or renamed event.

        Drives the REAL stream, then proves the ordered-equality check used by
        ``test_event_types_in_order`` is not a no-op: applying that exact check
        to a reordered / renamed copy of the LIVE-parsed sequence must fail.
        """
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=True)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.get(f"/api/carousels/{project_id}/workflow/stream")
        baseline = _event_types(_parse_sse(resp.text))
        # Sanity: the live baseline is the asserted contract order.
        assert baseline == [
            SSE_EVENT_PHASE_CHANGE,
            SSE_EVENT_PROGRESS,
            SSE_EVENT_ARTIFACT,
            SSE_EVENT_REVIEW_REQUIRED,
        ]
        reordered = [baseline[1], baseline[0], *baseline[2:]]
        renamed = [f"{baseline[0]}_renamed", *baseline[1:]]
        # The SAME equality the real test uses rejects both mutations.
        assert reordered != baseline
        assert renamed != baseline

    @pytest.mark.asyncio
    async def test_id_event_data_framing_and_keepalive_ignored(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: every event uses id:+event:+data: framing; keep-alive ignored.

        The fixture interleaves a keep-alive between progress and artifact; the
        parsed (non-keepalive) ids must still be contiguous from 1.
        """
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=True)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.get(f"/api/carousels/{project_id}/workflow/stream")
        # Keep-alive comment is present in the raw stream but dropped by parser.
        assert ": keepalive" in resp.text
        events = _parse_sse(resp.text)
        assert events
        ids = [event_id for event_id, _t, _d in events]
        assert all(isinstance(i, int) for i in ids)
        assert ids == list(range(1, len(ids) + 1))
        # Every parsed event carried an ``event:`` line and JSON ``data:``.
        for _id, event_type, data in events:
            assert event_type
            assert isinstance(data, dict)
            assert data[SSE_PAYLOAD_FIELD_EVENT] == event_type

    @pytest.mark.asyncio
    async def test_last_event_id_is_ignored(
        self, wf_env: WfEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Workflow stream ignores Last-Event-ID (current contract).

        This stream does NOT implement resume; ids always restart at 1 even when
        Last-Event-ID is supplied. Captures the true current contract — a
        refactor that silently added resume support would break this.
        """
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=True)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.get(
                f"/api/carousels/{project_id}/workflow/stream",
                headers={"Last-Event-ID": "10"},
            )
        events = _parse_sse(resp.text)
        ids = [event_id for event_id, _t, _d in events]
        assert ids[0] == 1
        assert ids == list(range(1, len(ids) + 1))


# ==============================================================================
# Golden snapshots — deterministic byte-identical baselines (AE-0107/0110/0111)
# ==============================================================================
class TestWorkflowSnapshots:
    """Workflow state/start/resume golden snapshots (body + status)."""

    async def _check(self, name: str, resp: Response, *, update: bool) -> None:
        if update:
            editorial_snapshot.write_snapshot(name, resp)
            return
        editorial_snapshot.assert_matches_snapshot(name, resp)

    @pytest.mark.asyncio
    async def test_snapshot_state(
        self,
        wf_env: WfEnv,
        snapshot_update: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Golden: GET /workflow/state (200) incl. artifact URL fields."""
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=True)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.get(f"/api/carousels/{project_id}/workflow/state")
        await self._check("workflow_state", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_state_not_found(
        self,
        wf_env: WfEnv,
        snapshot_update: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Golden: GET /workflow/state (404 no checkpoint)."""
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=False)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.get(f"/api/carousels/{project_id}/workflow/state")
        await self._check("workflow_state_not_found", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_start(
        self,
        wf_env: WfEnv,
        snapshot_update: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Golden: POST /workflow/start (200)."""
        project_id = await wf_env.seed_project(wf_env.editor)
        _patch_service(monkeypatch, project_id, has_state=False)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.post(
                f"/api/carousels/{project_id}/workflow/start",
                json={
                    "topic": "Fixture topic",
                    "audience": "Fixture audience",
                    "brief": "Fixture brief",
                    "sources": [],
                },
            )
        await self._check("workflow_start", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_resume(
        self,
        wf_env: WfEnv,
        snapshot_update: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Golden: POST /workflow/resume (202)."""
        project_id = await wf_env.seed_project(wf_env.editor, lock_version=1)
        _patch_service(monkeypatch, project_id, has_state=True)
        _patch_no_background_resume(monkeypatch)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.post(
                f"/api/carousels/{project_id}/workflow/resume",
                json={"action": "approve", "expected_version": 1},
            )
        await self._check("workflow_resume", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_resume_version_conflict(
        self,
        wf_env: WfEnv,
        snapshot_update: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Golden: POST /workflow/resume (409 stale version)."""
        project_id = await wf_env.seed_project(wf_env.editor, lock_version=1)
        _patch_service(monkeypatch, project_id, has_state=True)
        _patch_no_background_resume(monkeypatch)
        async with wf_env.client_for(wf_env.editor) as client:
            resp = await client.post(
                f"/api/carousels/{project_id}/workflow/resume",
                json={"action": "approve", "expected_version": 42},
            )
        await self._check(
            "workflow_resume_version_conflict", resp, update=snapshot_update
        )
