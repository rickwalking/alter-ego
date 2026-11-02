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
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.artifact_manifest import (
    CarouselArtifactManifest,
)
from rag_backend.application.services.carousel.cover_render_guard import (
    cover_identity,
    unreviewed_cover_refusal,
)
from rag_backend.application.services.carousel.editorial_finalize import (
    finalize_carousel_after_images_approval,
)
from rag_backend.domain.constants.artifact_build import (
    ARTIFACT_MANIFEST_FILENAME,
    ARTIFACT_VERSIONS_DIR,
)
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_CHANGE_REQUIRES_REVIEW,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.carousel_republish_sweeper import (
    CarouselRepublishSweeperConfig,
    CarouselRepublishSweeperRepository,
)
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


def _manifest(output_dir: Path, recorded: str | None) -> None:
    version_root = output_dir / ARTIFACT_VERSIONS_DIR / _VERSION
    version_root.mkdir(parents=True)
    payload: dict[str, object] = {"artifact_version": _VERSION}
    if recorded is not None:
        payload["slide_one_cover"] = recorded
    (version_root / ARTIFACT_MANIFEST_FILENAME).write_text(json.dumps(payload))


async def _carousel(
    built: Harness, dirs: Path, values: dict[str, object]
) -> tuple[str, list[str], Path]:
    output_dir = dirs.parent / "out" / uuid4().hex
    project_id, photos = await seed(
        built, dirs, output_dir=str(output_dir), artifact_version=_VERSION, **values
    )
    return project_id, photos, output_dir


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
        _manifest(output_dir, str(uuid4()))

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
    """A marked approved carousel whose cover changed is never rendered by the sweep."""
    # Scenario: A render never changes slide 1's cover on an approved carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        marked = datetime.now(UTC) - timedelta(hours=1)
        project_id, _, output_dir = await _carousel(
            built,
            dirs,
            {"workflow_status": _APPROVED, "needs_republish_since": marked},
        )
        _manifest(output_dir, str(uuid4()))
        sweeper = CarouselRepublishSweeperRepository(
            CarouselRepublishSweeperConfig(min_age_seconds=0)
        )

        with capture_logs() as logs:
            async with built.sessions()() as session:
                assert await sweeper.sweep(session) == 0

        assert (await row(built, project_id)).needs_republish_since is not None
        refused = [e for e in logs if e["event"] == "editorial_finalize_cover_refused"]
        assert [e["error"] for e in refused] == [ERR_COVER_CHANGE_REQUIRES_REVIEW]


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
        _manifest(same_dir, photos[0])
        draft_id, _, draft_dir = await _carousel(built, dirs, {})
        _manifest(draft_dir, str(uuid4()))
        legacy_id, _, legacy_dir = await _carousel(built, dirs, {"is_public": True})
        _manifest(legacy_dir, None)
        public_id, _, public_dir = await _carousel(built, dirs, {"is_public": True})
        _manifest(public_dir, str(uuid4()))

        assert await _refusal(built, same_id) is None
        assert await _refusal(built, draft_id) is None
        assert await _refusal(built, legacy_id) is None
        assert await _refusal(built, public_id) == ERR_COVER_CHANGE_REQUIRES_REVIEW


@requires_postgres
@pytest.mark.asyncio
async def test_a_build_records_the_cover_it_rendered(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The manifest field round-trips and a build records the slide-1 cover."""
    # Scenario: A render never changes slide 1's cover on an approved carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos, _ = await _carousel(built, dirs, {})
        async with built.sessions()() as session:
            project = await CarouselAutomationAcl(session).load_project(project_id)
        assert project is not None

        assert cover_identity(project) == photos[0]
        manifest = CarouselArtifactManifest(
            project_id=project_id,
            artifact_version=_VERSION,
            presentation_policy_version="v1",
            presentation_policy_checksum=None,
            template_version="t",
            renderer_contract_version="r",
            exporter_contract_version="e",
            source_lock_version=3,
            expected_slide_numbers=(1,),
            pt_source_hash="p",
            en_source_hash="e",
            slide_one_cover=cover_identity(project),
        )
        assert manifest.to_payload().slide_one_cover == photos[0]
