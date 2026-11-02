"""No render puts an unreviewed slide-1 cover on an approved carousel, on Postgres.

Feature: tests/features/website_cover_review_switch_ae0594.feature. The real
finalize step (what the republish service, the republish sweep, a slide edit's
republish and a manual republish all run) over a seeded carousel whose active
artifact version records the cover it rendered. Skipped without a Postgres
``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import update
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.artifact_build_support import (
    build_manifest,
    write_manifest,
)
from rag_backend.application.services.carousel.artifact_build_types import (
    ArtifactBuildRequest,
)
from rag_backend.application.services.carousel.artifact_manifest import (
    CarouselArtifactManifest,
)
from rag_backend.application.services.carousel.cover_render_guard import (
    unreviewed_cover_refusal,
)
from rag_backend.application.services.carousel.editorial_finalize import (
    finalize_carousel_after_images_approval,
)
from rag_backend.domain.constants.artifact_build import (
    ARTIFACT_MANIFEST_FILENAME,
    ARTIFACT_VERSIONS_DIR,
)
from rag_backend.domain.constants.carousel_slide_edit import (
    LOG_EVENT_REPUBLISH_COVER_REFUSED,
)
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_CHANGE_REQUIRES_REVIEW,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.carousel_republish_sweeper import (
    CarouselRepublishSweeperConfig,
    CarouselRepublishSweeperRepository,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.public import CarouselAutomationAcl
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.website_cover_review_pg_support import (
    Harness,
    harness,
    row,
    seed,
    tables,
)

_VERSION = "v-approved"
_APPROVED = "approved_for_publish"


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "out"))
    get_settings.cache_clear()
    yield assets
    get_settings.cache_clear()


async def _built_manifest(built: Harness, project_id: str) -> CarouselArtifactManifest:
    """The manifest the real build writes for the carousel as it is now."""
    async with built.sessions()() as session:
        project = await CarouselAutomationAcl(session).load_project(project_id)
    assert project is not None and project.output_dir
    staging = Path(project.output_dir) / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    request = ArtifactBuildRequest(
        project=project, slides=[], source_lock_version=3, prior_artifact_version=None
    )
    return build_manifest(request, _VERSION, staging)


async def _manifest(built: Harness, project_id: str, recorded: str | None) -> Path:
    """Write the active version's manifest recording ``recorded`` (None: legacy)."""
    manifest = replace(
        await _built_manifest(built, project_id), slide_one_cover=recorded
    )
    model = await row(built, project_id)
    version_root = Path(str(model.output_dir)) / ARTIFACT_VERSIONS_DIR / _VERSION
    version_root.mkdir(parents=True, exist_ok=True)
    path = version_root / ARTIFACT_MANIFEST_FILENAME
    write_manifest(path, manifest)
    if recorded is None:
        payload = json.loads(path.read_text())
        payload.pop("slide_one_cover")
        path.write_text(json.dumps(payload))
    return path


async def _carousel(
    built: Harness, dirs: Path, values: dict[str, object]
) -> tuple[str, list[str], Path]:
    output_dir = dirs.parent / "out" / uuid4().hex
    project_id, photos = await seed(
        built, dirs, output_dir=str(output_dir), artifact_version=_VERSION, **values
    )
    return project_id, photos, output_dir


async def _set_version(built: Harness, project_id: str, version: int) -> None:
    async with built.sessions()() as session:
        await session.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == project_id)
            .values(lock_version=version)
        )
        await session.commit()


async def _refusal(built: Harness, project_id: str) -> str | None:
    async with built.sessions()() as session:
        project = await CarouselAutomationAcl(session).load_project(project_id)
        assert project is not None
        return await unreviewed_cover_refusal(session, project)


@requires_postgres
@pytest.mark.asyncio
async def test_finalize_refuses_a_changed_cover_on_an_approved_carousel(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The active version rendered another cover: no re-render, the slides stay."""
    # Scenario: A render never changes slide 1's cover on an approved carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, _, output_dir = await _carousel(
            built, dirs, {"workflow_status": _APPROVED}
        )
        await _manifest(built, project_id, str(uuid4()))

        async with built.sessions()() as session:
            result = await finalize_carousel_after_images_approval(session, project_id)

        assert result.completed is False
        assert result.errors == (ERR_COVER_CHANGE_REQUIRES_REVIEW,)
        assert (await row(built, project_id)).status == "completed"


@requires_postgres
@pytest.mark.asyncio
async def test_the_sweep_refuses_a_changed_cover_on_an_approved_carousel(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Never rendered by the sweep, and retried only once the row changes."""
    # Scenario: A render never changes slide 1's cover on an approved carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        marked = datetime.now(UTC) - timedelta(hours=1)
        project_id, _, output_dir = await _carousel(
            built,
            dirs,
            {"workflow_status": _APPROVED, "needs_republish_since": marked},
        )
        await _manifest(built, project_id, str(uuid4()))
        sweeper = CarouselRepublishSweeperRepository(
            CarouselRepublishSweeperConfig(min_age_seconds=0)
        )

        with capture_logs() as logs:
            for _ in range(3):
                async with built.sessions()() as session:
                    assert await sweeper.sweep(session) == 0

        assert (await row(built, project_id)).needs_republish_since is not None
        refused = [e for e in logs if e["event"] == "editorial_finalize_cover_refused"]
        assert [e["error"] for e in refused] == [ERR_COVER_CHANGE_REQUIRES_REVIEW]
        flagged = [e for e in logs if e["event"] == LOG_EVENT_REPUBLISH_COVER_REFUSED]
        assert [e["log_level"] for e in flagged] == ["error"]

        await _set_version(built, project_id, 9)
        with capture_logs() as later:
            async with built.sessions()() as session:
                await sweeper.sweep(session)
        assert [e for e in later if e["event"] == "editorial_finalize_cover_refused"]


@requires_postgres
@pytest.mark.asyncio
async def test_the_guard_only_refuses_a_changed_cover_on_approved_or_public(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same cover, a draft, or a version without a record: the render may run."""
    # Scenario: A render never changes slide 1's cover on an approved carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        same_id, photos, same_dir = await _carousel(
            built, dirs, {"workflow_status": _APPROVED}
        )
        await _manifest(built, same_id, photos[0])
        draft_id, _, draft_dir = await _carousel(built, dirs, {})
        await _manifest(built, draft_id, str(uuid4()))
        legacy_id, _, legacy_dir = await _carousel(built, dirs, {"is_public": True})
        await _manifest(built, legacy_id, None)
        public_id, _, public_dir = await _carousel(built, dirs, {"is_public": True})
        await _manifest(built, public_id, str(uuid4()))

        assert await _refusal(built, same_id) is None
        assert await _refusal(built, draft_id) is None
        assert await _refusal(built, legacy_id) is None
        assert await _refusal(built, public_id) == ERR_COVER_CHANGE_REQUIRES_REVIEW


@requires_postgres
@pytest.mark.asyncio
async def test_a_build_records_the_cover_it_rendered(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real manifest build and writer record slide 1's cover in the JSON."""
    # Scenario: A render never changes slide 1's cover on an approved carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos, _ = await _carousel(built, dirs, {})
        path = Path(str((await row(built, project_id)).output_dir)) / "m.json"

        write_manifest(path, await _built_manifest(built, project_id))

        assert json.loads(path.read_text())["slide_one_cover"] == photos[0]
