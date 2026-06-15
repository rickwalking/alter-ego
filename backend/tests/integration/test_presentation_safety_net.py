"""Presentation byte-identical safety-net tests (AE-0116).

Behavioral + golden-snapshot safety net for the Phase 5 carousel PRESENTATION
extraction. Phase 5 moves the presentation routes/services/persistence (design /
blog / blog-i18n / slides / strategies / creator-asset) behind a facade + ACL;
the later slices (AE-0118 / AE-0120 / AE-0121) diff the live response against the
committed baseline this module captures on the current, pre-refactor code.

What is asserted:

* JSON responses — GET ``design``, ``blog``, ``blog/{lang}``, ``slides``,
  ``/strategies`` and the creator-asset upload — are captured as TRUE
  byte-identical golden snapshots (diff == 0). Volatile fields (``id`` /
  ``project_id`` / ``owner_id`` UUIDs, timestamps, and the WebP-derived
  ``content_sha256`` / ``relative_path``) are normalized deterministically by the
  diff helper (``tests/snapshots/presentation/_snapshot``).
* FileResponse endpoints — GET ``pdf``, ``images/{fn}``,
  ``slide-images/{lang}/{fn}`` — are asserted for identical content-type +
  cache headers + a STABLE sha256 digest of the served bytes. The fixture stages
  deterministic artifact files (FIXED bytes) on disk so the digests reproduce.
* ``download`` — JSON list of artifact relative paths (the artifact URL/path
  strings the refactor must preserve).

The image-dependent paths NEVER call a live provider (no DALL-E / Gemini / OpenAI
key in this env): all artifact bytes are fixed fixtures, and the creator-asset
upload feeds a fixed in-memory PNG through the real WebP normalizer. DEBUG is
pinned (monkeypatch.setenv + settings cache clear) so every env-sensitive
setting is deterministic local vs CI — this exact local(DEBUG=true)/CI(DEBUG=
false) split broke the Phase-3 safety net (AE-0097 lesson).

Feature file: tests/features/carousel_presentation_safety_net.feature

Run with ``--snapshot-update`` (flag registered in tests/conftest.py) to
regenerate the committed golden snapshots from current, pre-refactor behavior.
"""

from __future__ import annotations

import hashlib
import io
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
    CarouselTheme,
    User,
    UserRole,
)
from tests.integration.conftest import TEST_SECRET, auth_headers_for, create_test_user
from tests.snapshots.presentation import _snapshot as presentation_snapshot

if TYPE_CHECKING:
    from fastapi import FastAPI
    from httpx import Response
    from sqlalchemy.ext.asyncio import AsyncEngine

    from rag_backend.domain.models.carousel import DesignTokens

# --- Constants -----------------------------------------------------------------
SNAPSHOT_UPDATE_OPTION = "--snapshot-update"
ANON_SECRET = "test-anon-secret-for-integration-tests"
OWNER_EMAIL = "pres-owner@integration.example.com"
OTHER_EMAIL = "pres-other@integration.example.com"

# Stable env values pinned for the presentation surface so derived strings
# (public slide-image URLs in the design tokens) are byte-identical local vs CI.
PUBLIC_BASE_URL = "https://fixture.example.com"

# Deterministic FIXED artifact bytes (NOT re-encoded) — FileResponse serves them
# verbatim, so a sha256 of these exact bytes is a reproducible digest contract.
PDF_BYTES_PT: Final = b"%PDF-1.4 fixture pt carousel bytes\n%%EOF\n"
PDF_BYTES_EN: Final = b"%PDF-1.4 fixture en carousel bytes\n%%EOF\n"
HERO_IMAGE_BYTES: Final = b"\xff\xd8\xff\xe0fixture-hero-jpeg-bytes\xff\xd9"
SLIDE_IMAGE_BYTES_PT: Final = b"\xff\xd8\xff\xe0fixture-slide-pt-bytes\xff\xd9"
SLIDE_IMAGE_BYTES_EN: Final = b"\xff\xd8\xff\xe0fixture-slide-en-bytes\xff\xd9"

SLIDE_COUNT: Final = 3
EXPECTED_MEDIA_TYPE_PDF = "application/pdf"
EXPECTED_MEDIA_TYPE_JPEG = "image/jpeg"

# Deterministic design tokens persisted on the project so the GET /design
# response (which merges DB tokens with the disk slide layout) is deterministic.
FIXTURE_DESIGN_TOKENS: Final[dict[str, object]] = {
    "colors": {
        "primary": "#3b82f6",
        "accent": "#f59e0b",
        "bg": "#0a0e17",
        "text": "#e2e8f0",
        "text_muted": "#94a3b8",
        "text_dim": "#64748b",
        "border": "#1e293b",
        "glow": "#f59e0b",
    },
    "typography": {
        "font_family_heading": "Inter, system-ui, sans-serif",
        "font_family_body": "Inter, system-ui, sans-serif",
        "font_family_badge": "JetBrains Mono, monospace",
    },
    "images": {"hero": "", "slides": []},
    "layout": {
        "badge_label": "FIXTURE",
        "swipe_text": "Swipe",
        "progress_segments": SLIDE_COUNT,
    },
}

FIXTURE_BLOG_PT = "# Fixture Title: Fixture Subtitle\n\nDeterministic blog body."
FIXTURE_BLOG_EN = "# Fixture Title EN: Fixture Subtitle EN\n\nDeterministic body."


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


def _stage_artifacts(output_dir: Path) -> None:
    """Stage deterministic on-disk artifacts (FIXED bytes) for the project.

    Layout mirrors the artifact serving roots the FileResponse resolvers read:
      <output>/images/slide_N.jpg     (shared hero/raw images)
      <output>/<lang>/slide_N.jpg     (rendered per-language slides)
      <output>/<lang>/carousel.pdf    (per-language PDF)
    """
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, SLIDE_COUNT + 1):
        (images_dir / f"slide_{i}.jpg").write_bytes(HERO_IMAGE_BYTES)

    for lang, slide_bytes in (
        ("pt", SLIDE_IMAGE_BYTES_PT),
        ("en", SLIDE_IMAGE_BYTES_EN),
    ):
        lang_dir = output_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, SLIDE_COUNT + 1):
            (lang_dir / f"slide_{i}.jpg").write_bytes(slide_bytes)

    (output_dir / "pt" / "carousel.pdf").write_bytes(PDF_BYTES_PT)
    (output_dir / "en" / "carousel.pdf").write_bytes(PDF_BYTES_EN)


class PresEnv:
    """Test environment: app + DB engine + seeding/client helpers."""

    def __init__(
        self, app: FastAPI, owner: User, other: User, output_dir: Path
    ) -> None:
        self._app = app
        self.owner = owner
        self.other = other
        self.output_dir = output_dir

    def client_for(self, user: User) -> AsyncClient:
        transport = ASGITransport(app=self._app)
        return AsyncClient(
            transport=transport,
            base_url="http://test",
            headers=auth_headers_for(user),
        )

    async def seed_project(self, *, is_public: bool) -> str:
        """Persist a completed, rendered carousel owned by ``self.owner``."""
        from rag_backend.infrastructure.database.carousel_repository import (
            PostgresCarouselRepository,
        )
        from rag_backend.infrastructure.database.config import get_session_maker

        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = PostgresCarouselRepository(session)
            project = CarouselProject(
                topic="Fixture topic",
                audience="Fixture audience",
                niche="FIXTURE",
                theme=CarouselTheme.AI_COMPETITION,
                owner_id=str(self.owner.id),
                is_public=is_public,
                status=CarouselStatus.COMPLETED,
                output_dir=str(self.output_dir),
                blog_markdown=FIXTURE_BLOG_PT,
                blog_translations={"pt": FIXTURE_BLOG_PT, "en": FIXTURE_BLOG_EN},
                design_tokens=cast("DesignTokens", FIXTURE_DESIGN_TOKENS),
                pdf_path=str(self.output_dir / "pt" / "carousel.pdf"),
                pdf_path_en=str(self.output_dir / "en" / "carousel.pdf"),
            )
            created = await repo.create_project(project)
            project_id = str(created.id)
            for i in range(1, SLIDE_COUNT + 1):
                slide = CarouselSlide(
                    project_id=created.id,
                    slide_number=i,
                    slide_type="content",
                    heading=f"Slide {i}",
                    body=f"Body {i}",
                    image_prompt=f"Prompt {i}",
                )
                await repo.create_slide(slide)
            await session.commit()
        return project_id


@pytest_asyncio.fixture
async def pres_env(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[PresEnv, None]:
    """File-backed DB + app with an owner + other editor and a staged project."""
    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.database.config import close_db

    assert isinstance(tmp_path, Path)
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = ANON_SECRET
    # Pin DEBUG + env-sensitive settings so the baseline is deterministic local
    # vs CI (AE-0097 lesson). monkeypatch.setenv auto-reverts at test end.
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("CAROUSEL_PUBLIC_BASE_URL", PUBLIC_BASE_URL)
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(tmp_path / "creator_assets"))
    get_settings.cache_clear()

    output_dir = tmp_path / "carousel-output"
    output_dir.mkdir()
    _stage_artifacts(output_dir)

    db_path = str(tmp_path / "pres_env.db")
    engine = await _make_engine(db_path)
    owner = await create_test_user(OWNER_EMAIL, UserRole.EDITOR)
    other = await create_test_user(OTHER_EMAIL, UserRole.EDITOR)
    app = create_app()
    env = PresEnv(app=app, owner=owner, other=other, output_dir=output_dir)
    try:
        yield env
    finally:
        db_config.c_engine = None
        await close_db()
        await engine.dispose()
        get_settings.cache_clear()


def _make_png_bytes() -> bytes:
    """Build a deterministic in-memory PNG for the creator-asset upload.

    Fixed dimensions/content so the normalized ``width``/``height`` are stable;
    no live provider, no network, no API key.
    """
    from PIL import Image

    image = Image.new("RGB", (256, 128), color=(10, 20, 30))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# ==============================================================================
# JSON response behavior + golden snapshots
# ==============================================================================
class TestDesignResponse:
    """GET /design (tests/features/carousel_presentation_safety_net.feature)."""

    @pytest.mark.asyncio
    async def test_design_returns_200_for_public(self, pres_env: PresEnv) -> None:
        """Scenario: design response unchanged for a rendered public carousel."""
        project_id = await pres_env.seed_project(is_public=True)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/design")
        assert resp.status_code == 200
        body = resp.json()
        assert body["theme_name"] == CarouselTheme.AI_COMPETITION.value
        assert body["layout"]["progress_segments"] == SLIDE_COUNT

    @pytest.mark.asyncio
    async def test_design_forbidden_when_not_public(self, pres_env: PresEnv) -> None:
        """Scenario: design route rejects a non-public carousel."""
        project_id = await pres_env.seed_project(is_public=False)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/design")
        assert resp.status_code == 404


class TestBlogResponse:
    """GET /blog and /blog/{lang}."""

    @pytest.mark.asyncio
    async def test_blog_default_returns_200(self, pres_env: PresEnv) -> None:
        """Scenario: default blog response unchanged."""
        project_id = await pres_env.seed_project(is_public=True)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/blog")
        assert resp.status_code == 200
        assert resp.json()["markdown"] == FIXTURE_BLOG_PT

    @pytest.mark.asyncio
    async def test_blog_i18n_en_returns_200(self, pres_env: PresEnv) -> None:
        """Scenario: i18n blog response unchanged for a translated language."""
        project_id = await pres_env.seed_project(is_public=True)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/blog/en")
        assert resp.status_code == 200
        body = resp.json()
        assert body["language"] == "en"
        assert body["available_languages"] == ["pt", "en"]


class TestSlidesResponse:
    """GET /slides (owner-scoped)."""

    @pytest.mark.asyncio
    async def test_slides_returns_200_for_owner(self, pres_env: PresEnv) -> None:
        """Scenario: slides list response unchanged for the owner."""
        project_id = await pres_env.seed_project(is_public=False)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/slides")
        assert resp.status_code == 200
        assert len(resp.json()) == SLIDE_COUNT

    @pytest.mark.asyncio
    async def test_slides_forbidden_for_non_owner(self, pres_env: PresEnv) -> None:
        """Scenario: slides list is forbidden for a non-owner editor."""
        project_id = await pres_env.seed_project(is_public=False)
        async with pres_env.client_for(pres_env.other) as client:
            resp = await client.get(f"/api/carousels/{project_id}/slides")
        assert resp.status_code == 403


class TestStrategyListing:
    """GET /strategies (registry-driven, deterministic, no DB)."""

    @pytest.mark.asyncio
    async def test_strategies_returns_200(self, pres_env: PresEnv) -> None:
        """Scenario: strategy listing response unchanged."""
        project_id = await pres_env.seed_project(is_public=False)
        del project_id
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get("/api/carousels/strategies")
        assert resp.status_code == 200
        strategies = resp.json()["strategies"]
        assert strategies
        for entry in strategies:
            assert entry["name"]
            assert entry["display_name"]


class TestCreatorAssetUpload:
    """POST /creator-asset/upload (deterministic fixed-bytes PNG, no provider)."""

    @pytest.mark.asyncio
    async def test_upload_returns_201(self, pres_env: PresEnv) -> None:
        """Scenario: creator-asset upload response unchanged.

        The fixed in-memory PNG normalizes to a fixed-size WebP; ``width`` /
        ``height`` / ``media_type`` are the stable contract asserted here, while
        the WebP-derived ``content_sha256`` is version-sensitive (normalized in
        the snapshot helper).
        """
        project_id = await pres_env.seed_project(is_public=False)
        png = _make_png_bytes()
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.post(
                f"/api/carousels/{project_id}/creator-asset/upload",
                files={"file": ("brand.png", png, "image/png")},
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["media_type"] == "image/webp"
        assert body["width"] == 256
        assert body["height"] == 128
        assert body["content_sha256"]


# ==============================================================================
# FileResponse endpoints — content-type + headers + stable byte digest
# ==============================================================================
def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestFileResponseArtifacts:
    """PDF + JPEG endpoints: content-type, cache headers, byte digest."""

    @pytest.mark.asyncio
    async def test_pdf_bytes_and_headers(self, pres_env: PresEnv) -> None:
        """Scenario: pdf bytes + headers + content-type unchanged (digest)."""
        project_id = await pres_env.seed_project(is_public=True)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/pdf?lang=pt")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == EXPECTED_MEDIA_TYPE_PDF
        assert f"carousel-{project_id}-pt.pdf" in resp.headers["content-disposition"]
        assert _sha256(resp.content) == _sha256(PDF_BYTES_PT)

    @pytest.mark.asyncio
    async def test_pdf_en_bytes_distinct_digest(self, pres_env: PresEnv) -> None:
        """Scenario: per-language pdf serves the language-specific bytes."""
        project_id = await pres_env.seed_project(is_public=True)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/pdf?lang=en")
        assert resp.status_code == 200
        assert _sha256(resp.content) == _sha256(PDF_BYTES_EN)
        assert _sha256(PDF_BYTES_EN) != _sha256(PDF_BYTES_PT)

    @pytest.mark.asyncio
    async def test_hero_image_bytes_and_headers(self, pres_env: PresEnv) -> None:
        """Scenario: hero image bytes + content-type + cache headers unchanged."""
        project_id = await pres_env.seed_project(is_public=True)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/images/slide_1.jpg")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == EXPECTED_MEDIA_TYPE_JPEG
        assert "cache-control" in resp.headers
        assert _sha256(resp.content) == _sha256(HERO_IMAGE_BYTES)

    @pytest.mark.asyncio
    async def test_slide_image_bytes_per_language(self, pres_env: PresEnv) -> None:
        """Scenario: per-language slide image serves the language-specific bytes."""
        project_id = await pres_env.seed_project(is_public=True)
        async with pres_env.client_for(pres_env.owner) as client:
            resp_pt = await client.get(
                f"/api/carousels/{project_id}/slide-images/pt/slide_1.jpg"
            )
            resp_en = await client.get(
                f"/api/carousels/{project_id}/slide-images/en/slide_1.jpg"
            )
        assert resp_pt.status_code == 200
        assert resp_en.status_code == 200
        assert resp_pt.headers["content-type"] == EXPECTED_MEDIA_TYPE_JPEG
        assert _sha256(resp_pt.content) == _sha256(SLIDE_IMAGE_BYTES_PT)
        assert _sha256(resp_en.content) == _sha256(SLIDE_IMAGE_BYTES_EN)


class TestDownloadArtifactPaths:
    """GET /download: artifact URL/path strings the refactor must preserve."""

    @pytest.mark.asyncio
    async def test_download_lists_relative_paths(self, pres_env: PresEnv) -> None:
        """Scenario: download lists the staged artifact relative paths."""
        project_id = await pres_env.seed_project(is_public=False)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/download")
        assert resp.status_code == 200
        files = set(resp.json()["files"])
        assert "output_dir" not in resp.json()
        expected = {
            str(Path("images") / f"slide_{i}.jpg") for i in range(1, SLIDE_COUNT + 1)
        }
        expected |= {
            str(Path(lang) / f"slide_{i}.jpg")
            for lang in ("pt", "en")
            for i in range(1, SLIDE_COUNT + 1)
        }
        expected |= {str(Path(lang) / "carousel.pdf") for lang in ("pt", "en")}
        assert expected <= files


# ==============================================================================
# Golden snapshots — deterministic byte-identical baselines (AE-0118/0120/0121)
# ==============================================================================
class TestPresentationSnapshots:
    """Design/blog/slides/strategies/creator-asset golden snapshots."""

    async def _check(self, name: str, resp: Response, *, update: bool) -> None:
        if update:
            presentation_snapshot.write_snapshot(name, resp)
            return
        presentation_snapshot.assert_matches_snapshot(name, resp)

    @pytest.mark.asyncio
    async def test_snapshot_design(
        self, pres_env: PresEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /design (200)."""
        project_id = await pres_env.seed_project(is_public=True)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/design")
        await self._check("design", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_blog(
        self, pres_env: PresEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /blog (200)."""
        project_id = await pres_env.seed_project(is_public=True)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/blog")
        await self._check("blog", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_blog_i18n(
        self, pres_env: PresEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /blog/{lang} (200)."""
        project_id = await pres_env.seed_project(is_public=True)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/blog/en")
        await self._check("blog_i18n_en", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_slides(
        self, pres_env: PresEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /slides (200)."""
        project_id = await pres_env.seed_project(is_public=False)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/slides")
        await self._check("slides", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_strategies(
        self, pres_env: PresEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /strategies (200)."""
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get("/api/carousels/strategies")
        await self._check("strategies", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_creator_asset_upload(
        self, pres_env: PresEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /creator-asset/upload (201)."""
        project_id = await pres_env.seed_project(is_public=False)
        png = _make_png_bytes()
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.post(
                f"/api/carousels/{project_id}/creator-asset/upload",
                files={"file": ("brand.png", png, "image/png")},
            )
        await self._check("creator_asset_upload", resp, update=snapshot_update)


# ==============================================================================
# Falsifiability guard — the snapshot/digest checks are not no-ops
# ==============================================================================
class TestSafetyNetIsFalsifiable:
    """Prove the byte-identical assertions reject a mutated payload."""

    @pytest.mark.asyncio
    async def test_digest_detects_mutated_bytes(self, pres_env: PresEnv) -> None:
        """Scenario: a one-byte artifact mutation changes the asserted digest."""
        project_id = await pres_env.seed_project(is_public=True)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/pdf?lang=pt")
        live = _sha256(resp.content)
        assert live == _sha256(PDF_BYTES_PT)
        assert live != _sha256(PDF_BYTES_PT + b"x")

    @pytest.mark.asyncio
    async def test_snapshot_diff_detects_mutation(self, pres_env: PresEnv) -> None:
        """Scenario: the snapshot diff is non-empty for a mutated response."""
        project_id = await pres_env.seed_project(is_public=True)
        async with pres_env.client_for(pres_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/blog")
        # Live response matches the committed baseline.
        assert presentation_snapshot.diff_snapshot("blog", resp) == []
        # A mutated copy of the SAME response must be rejected by the same check.
        snapshot = presentation_snapshot.build_snapshot(resp)
        mutated = presentation_snapshot.load_snapshot("blog")
        assert mutated == snapshot
        body = mutated["body"]
        assert isinstance(body, dict)
        body["markdown"] = "MUTATED"
        assert mutated != snapshot
