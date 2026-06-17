"""Publishing byte-identical safety-net tests (AE-0125).

Behavioral + golden-snapshot safety net for the Phase 6 PUBLISHING extraction.
Phase 6 moves blog/publishing/distribution + read routes behind facades + an
ACL and adds an additive migration + an outbox; the later slices (AE-0128 /
AE-0129 / AE-0131) diff the live response against the committed baseline this
module captures on the current, pre-refactor code (diff == 0).

What is asserted as TRUE byte-identical golden snapshots (volatile UUID /
timestamp / date fields normalized by ``tests/snapshots/publishing/_snapshot``):

* blog-post CRUD — POST / GET / list / PUT / DELETE ``/api/blog-posts``;
* the public carousel blog — GET ``/api/carousels/{id}/blog`` + ``/blog/{lang}``;
* publish + caption distribution — POST ``/api/carousels/{id}/publish/instagram``
  + ``/api/carousels/{id}/caption``;
* content-calendar — GET ``/api/content-calendar``;
* workflow-board — GET ``/api/workflow-board``;
* editorial-analytics — GET ``/api/editorial-analytics``;
* the carousel publish flow — POST ``/api/carousels/{id}/publish`` which sets
  ``is_public=True`` (the current approval->release conflation). Capturing THIS
  behavior is the contract AE-0128's release command must diff to zero against.

External channels are DETERMINISTICALLY stubbed and never call a live provider
(no Meta / Instagram / OpenAI key in this env): the Instagram publisher is an
in-memory ``_StubPublisher`` injected via the container override, and the
caption route reads the project's persisted caption (no LLM call). The
artifact-health gate (which would require staging real rendered JPEG/PDF files)
is replaced at the route module level with a no-op stub — a test seam mirroring
the AE-0097 module-level patch; no production code is modified.

DEBUG + every env-sensitive setting (cookie ``secure``, the public base URL) are
pinned (monkeypatch.setenv + settings cache clear) so the baseline is
deterministic local vs CI — the exact local(DEBUG=true)/CI(DEBUG=false) split
broke the Phase-3 safety net (AE-0097 lesson).

Feature file: tests/features/carousel_publishing_safety_net.feature

Run with ``--snapshot-update`` (flag registered in tests/conftest.py) to
regenerate the committed golden snapshots from current, pre-refactor behavior.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final, cast

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_STATUS_AWAITING_HUMAN,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
    CarouselTheme,
    User,
    UserRole,
)
from rag_backend.domain.protocols import PublishResult
from tests.integration.conftest import TEST_SECRET, auth_headers_for, create_test_user
from tests.snapshots.publishing import _snapshot as publishing_snapshot

if TYPE_CHECKING:
    from fastapi import FastAPI
    from httpx import Response
    from sqlalchemy.ext.asyncio import AsyncEngine

    from rag_backend.domain.models.carousel import DesignTokens

# --- Constants -----------------------------------------------------------------
SNAPSHOT_UPDATE_OPTION = "--snapshot-update"
ANON_SECRET = "test-anon-secret-for-integration-tests"
OWNER_EMAIL = "pub-owner@integration.example.com"
OTHER_EMAIL = "pub-other@integration.example.com"

# Pinned so the Instagram public-image URLs the publisher receives are stable.
PUBLIC_BASE_URL = "https://fixture.example.com"

# Deterministic carousel content used across publish / blog / caption snapshots.
FIXTURE_TITLE = "Fixture Title"
FIXTURE_SUBTITLE = "Fixture Subtitle"
FIXTURE_BLOG_PT = "# Fixture Title: Fixture Subtitle\n\nDeterministic blog body."
FIXTURE_BLOG_EN = "# Fixture Title EN: Fixture Subtitle EN\n\nDeterministic body."
FIXTURE_CAPTION = "Deterministic fixture caption for the snapshot."
# AE-0204: LinkedIn fixtures + a poison value used to prove readers source the
# canonical ``blog_posts.distribution`` home, never the embedded carousel column.
_FIXTURE_LINKEDIN_PT = "Deterministic LinkedIn post (PT) for the home."
_FIXTURE_LINKEDIN_EN = "Deterministic LinkedIn post (EN) for the home."
_POISON_CAPTION = "POISON-EMBEDDED-CAPTION-MUST-NOT-BE-READ"
SLIDE_COUNT: Final = 3

# A STABLE output_dir string (the publish/caption JSON surfaces it). The
# artifact-health gate is stubbed, so no real directory needs to exist.
FIXTURE_OUTPUT_DIR = "/fixture/carousel-output"
FIXTURE_PDF_PATH = "/fixture/carousel-output/pt/carousel.pdf"
FIXTURE_PDF_PATH_EN = "/fixture/carousel-output/en/carousel.pdf"

# Deterministic Instagram publish result (the stub never calls Meta).
STUB_IG_POST_ID = "IG_FIXTURE_POST_ID"

# Deterministic design tokens persisted so the publish response is stable.
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

# Deterministic blog-post payload for the CRUD snapshots.
FIXTURE_BLOG_POST_TITLE = "Fixture Blog Post"
FIXTURE_BLOG_POST_SLUG = "fixture-blog-post"
FIXTURE_BLOG_POST_CONTENT: Final[dict[str, object]] = {
    "blocks": [{"type": "paragraph", "text": "Deterministic blog post body."}],
}
FIXTURE_BLOG_POST_EXCERPT = "Deterministic excerpt."
FIXTURE_BLOG_POST_KEYWORDS: Final[list[str]] = ["fixture", "snapshot"]

# A fixed scheduled-publish instant so the content-calendar entry is captured.
FIXTURE_SCHEDULED_AT = datetime(2026, 6, 20, 12, 0, 0, tzinfo=UTC)
CALENDAR_BLOG_TITLE = "Calendar Fixture Post"
CALENDAR_BLOG_SLUG = "calendar-fixture-post"


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


class _StubPublisher:
    """Deterministic in-memory SocialPublisher (never calls Meta/Instagram).

    Records the caption + image URLs it was handed so behavior tests can assert
    the route built the public URLs, and returns a FIXED published result so the
    publish/instagram response snapshot is byte-deterministic.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    async def publish_instagram(
        self, caption: str, image_urls: list[str]
    ) -> PublishResult:
        self.calls.append((caption, list(image_urls)))
        return PublishResult(status="published", post_id=STUB_IG_POST_ID)


def _stub_artifact_health(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the route-level artifact-health gate with a no-op.

    The real gate requires staging valid rendered JPEG/PDF artifacts on disk;
    it is NOT part of any JSON response under test. Both the crud publish route
    and the publishing route import ``assert_carousel_artifacts_healthy`` at
    module level, so patching that name on each module injects the no-op at the
    app edge (mirrors the AE-0097 module-level patch). No src/ is modified.
    """
    from rag_backend.api.routes.carousels import crud as crud_module
    from rag_backend.api.routes.carousels import publishing as publishing_module

    def _ok(_project: CarouselProject, _slides: Sequence[CarouselSlide]) -> None:
        return None

    monkeypatch.setattr(crud_module, "assert_carousel_artifacts_healthy", _ok)
    monkeypatch.setattr(publishing_module, "assert_carousel_artifacts_healthy", _ok)


class PubEnv:
    """Test environment: app + DB engine + seeding/client helpers."""

    def __init__(self, app: FastAPI, owner: User, other: User) -> None:
        self._app = app
        self.owner = owner
        self.other = other

    def client_for(self, user: User) -> AsyncClient:
        transport = ASGITransport(app=self._app)
        return AsyncClient(
            transport=transport,
            base_url="http://test",
            headers=auth_headers_for(user),
        )

    async def seed_carousel(
        self, *, is_public: bool, approved_for_publish: bool
    ) -> str:
        """Persist a completed carousel owned by ``self.owner``.

        The project carries deterministic blog/caption/design content and stable
        artifact path strings; ``workflow_status`` is set to approved-for-publish
        when requested so the publish + instagram routes pass their release gate.
        """
        from rag_backend.infrastructure.database.carousel_repository import (
            PostgresCarouselRepository,
        )
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

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
                title=FIXTURE_TITLE,
                subtitle=FIXTURE_SUBTITLE,
                output_dir=FIXTURE_OUTPUT_DIR,
                generate_images=False,
                blog_markdown=FIXTURE_BLOG_PT,
                blog_translations={"pt": FIXTURE_BLOG_PT, "en": FIXTURE_BLOG_EN},
                caption=FIXTURE_CAPTION,
                design_tokens=cast("DesignTokens", FIXTURE_DESIGN_TOKENS),
                pdf_path=FIXTURE_PDF_PATH,
                pdf_path_en=FIXTURE_PDF_PATH_EN,
                current_phase=PHASE_CONTENT,
                phase_status=PHASE_STATUS_AWAITING_HUMAN,
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
            if approved_for_publish:
                model = await session.get(CarouselProjectModel, project_id)
                assert model is not None
                model.workflow_status = WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
            await session.commit()
        return project_id

    async def seed_calendar_blog_post(self) -> str:
        """Persist a blog post with a fixed scheduled-publish instant."""
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models import BlogPostModel

        session_maker = get_session_maker()
        async with session_maker() as session:
            post = BlogPostModel.from_entity({
                "title": CALENDAR_BLOG_TITLE,
                "slug": CALENDAR_BLOG_SLUG,
                "status": "scheduled",
                "content": {},
                "author_id": str(self.owner.id),
                "scheduled_publish_at": FIXTURE_SCHEDULED_AT,
            })
            session.add(post)
            await session.commit()
            return str(post.id)


@pytest_asyncio.fixture
async def pub_env(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[PubEnv, None]:
    """File-backed DB + app with an owner + other editor and client helpers."""
    from pathlib import Path

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.database.config import close_db

    assert isinstance(tmp_path, Path)
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = ANON_SECRET
    # Pin DEBUG + the public base URL so every env-sensitive setting is
    # deterministic local vs CI (AE-0097 lesson). monkeypatch reverts at end.
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("CAROUSEL_PUBLIC_BASE_URL", PUBLIC_BASE_URL)
    get_settings.cache_clear()

    db_path = str(tmp_path / "pub_env.db")
    engine = await _make_engine(db_path)
    owner = await create_test_user(OWNER_EMAIL, UserRole.EDITOR)
    other = await create_test_user(OTHER_EMAIL, UserRole.EDITOR)
    app = create_app()
    env = PubEnv(app=app, owner=owner, other=other)
    try:
        yield env
    finally:
        db_config.c_engine = None
        await close_db()
        await engine.dispose()
        get_settings.cache_clear()


def _blog_post_create_payload() -> dict[str, object]:
    return {
        "title": FIXTURE_BLOG_POST_TITLE,
        "slug": FIXTURE_BLOG_POST_SLUG,
        "content": FIXTURE_BLOG_POST_CONTENT,
        "excerpt": FIXTURE_BLOG_POST_EXCERPT,
        "keywords": FIXTURE_BLOG_POST_KEYWORDS,
    }


async def _create_blog_post(client: AsyncClient) -> Response:
    return await client.post("/api/blog-posts", json=_blog_post_create_payload())


def _override_publisher(env: PubEnv) -> _StubPublisher:
    """Override the container's Instagram publisher with the deterministic stub."""
    from rag_backend.infrastructure.container import get_container

    stub = _StubPublisher()
    get_container().instagram_publisher.override(stub)
    return stub


def _reset_publisher() -> None:
    from rag_backend.infrastructure.container import get_container

    get_container().instagram_publisher.reset_override()


# ==============================================================================
# Blog-post CRUD behavior + snapshots
# ==============================================================================
class TestBlogPostCrud:
    """POST/GET/list/PUT/DELETE /blog-posts (feature: publishing safety net)."""

    @pytest.mark.asyncio
    async def test_create_returns_201(self, pub_env: PubEnv) -> None:
        """Scenario: blog post create response unchanged."""
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await _create_blog_post(client)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == FIXTURE_BLOG_POST_TITLE
        assert body["slug"] == FIXTURE_BLOG_POST_SLUG
        assert body["status"] == "draft"

    @pytest.mark.asyncio
    async def test_get_returns_200(self, pub_env: PubEnv) -> None:
        """Scenario: blog post get response unchanged."""
        async with pub_env.client_for(pub_env.owner) as client:
            created = await _create_blog_post(client)
            post_id = created.json()["id"]
            resp = await client.get(f"/api/blog-posts/{post_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == post_id

    @pytest.mark.asyncio
    async def test_list_returns_200(self, pub_env: PubEnv) -> None:
        """Scenario: blog post list response unchanged."""
        async with pub_env.client_for(pub_env.owner) as client:
            await _create_blog_post(client)
            resp = await client.get("/api/blog-posts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == FIXTURE_BLOG_POST_TITLE

    @pytest.mark.asyncio
    async def test_update_requires_if_match(self, pub_env: PubEnv) -> None:
        """Scenario: blog post update requires the If-Match version header."""
        async with pub_env.client_for(pub_env.owner) as client:
            created = await _create_blog_post(client)
            post_id = created.json()["id"]
            resp = await client.put(
                f"/api/blog-posts/{post_id}", json={"title": "Renamed"}
            )
        assert resp.status_code == 428

    @pytest.mark.asyncio
    async def test_update_returns_200_with_if_match(self, pub_env: PubEnv) -> None:
        """Scenario: blog post update response unchanged with a valid version."""
        async with pub_env.client_for(pub_env.owner) as client:
            created = await _create_blog_post(client)
            post_id = created.json()["id"]
            resp = await client.put(
                f"/api/blog-posts/{post_id}",
                json={"excerpt": "Updated excerpt."},
                headers={"If-Match": "1"},
            )
        assert resp.status_code == 200
        assert resp.json()["excerpt"] == "Updated excerpt."
        assert resp.json()["lock_version"] == 2

    @pytest.mark.asyncio
    async def test_delete_returns_204(self, pub_env: PubEnv) -> None:
        """Scenario: blog post delete returns 204 and removes the post."""
        async with pub_env.client_for(pub_env.owner) as client:
            created = await _create_blog_post(client)
            post_id = created.json()["id"]
            resp = await client.delete(f"/api/blog-posts/{post_id}")
            after = await client.get(f"/api/blog-posts/{post_id}")
        assert resp.status_code == 204
        assert after.status_code == 404


# ==============================================================================
# Public carousel blog behavior + snapshots
# ==============================================================================
class TestPublicCarouselBlog:
    """GET /carousels/{id}/blog + /blog/{lang} (public surface)."""

    @pytest.mark.asyncio
    async def test_blog_returns_200_for_public(self, pub_env: PubEnv) -> None:
        """Scenario: public carousel blog response unchanged."""
        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=False
        )
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/blog")
        assert resp.status_code == 200
        assert resp.json()["markdown"] == FIXTURE_BLOG_PT

    @pytest.mark.asyncio
    async def test_blog_forbidden_when_not_public(self, pub_env: PubEnv) -> None:
        """Scenario: carousel blog is hidden (404) for a non-public carousel."""
        project_id = await pub_env.seed_carousel(
            is_public=False, approved_for_publish=False
        )
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/blog")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_blog_i18n_en_returns_200(self, pub_env: PubEnv) -> None:
        """Scenario: i18n carousel blog response unchanged for English."""
        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=False
        )
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/blog/en")
        assert resp.status_code == 200
        body = resp.json()
        assert body["language"] == "en"
        assert body["available_languages"] == ["pt", "en"]

    @pytest.mark.asyncio
    async def test_blog_with_ae0127_backfill_row_is_byte_identical(
        self, pub_env: PubEnv
    ) -> None:
        """Scenario: the ``origin='carousel'`` row (the production path) yields the
        byte-identical /blog response captured by the embedded golden snapshot.

        Post-AE-0163 the carousel repository dual-writes the canonical
        ``origin='carousel'`` blog_posts row on every blog write (the same shape as
        the AE-0127 backfill), so ``seed_carousel`` already creates it and the read
        path sources the body + 404 signal SOLELY from that row. This proves the
        row-path response is byte-identical to the embedded golden snapshot
        (``carousel_blog``) — the de-risking guarantee for the AE-0162 drop.
        """
        from sqlalchemy import select

        from rag_backend.domain.constants.blog_post import BlogPostOrigin
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models import BlogPostModel

        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=False
        )

        # The AE-0163 dual-write created exactly one carousel-origin row on seed.
        session_maker = get_session_maker()
        async with session_maker() as session:
            rows = (
                await session.execute(
                    select(BlogPostModel).where(
                        BlogPostModel.project_id == project_id,
                        BlogPostModel.origin == BlogPostOrigin.CAROUSEL.value,
                    )
                )
            ).scalars().all()
        assert len(rows) == 1
        row = rows[0]
        assert row.slug == f"carousel-{project_id}"
        assert row.title == FIXTURE_TITLE
        assert row.excerpt is None  # AE-0127 row shape preserved (excerpt NULL)
        assert row.content["markdown"] == FIXTURE_BLOG_PT

        async with pub_env.client_for(pub_env.owner) as client:
            with_row = await client.get(f"/api/carousels/{project_id}/blog")
        assert with_row.status_code == 200
        # Byte-identical via the row path to the committed embedded golden snapshot.
        assert publishing_snapshot.diff_snapshot("carousel_blog", with_row) == []


# ==============================================================================
# Distribution: caption + publish/instagram (deterministic channel stub)
# ==============================================================================
class TestDistribution:
    """POST /caption + /publish/instagram with a deterministic publisher."""

    @pytest.mark.asyncio
    async def test_caption_returns_persisted_caption(self, pub_env: PubEnv) -> None:
        """Scenario: generate-caption returns the persisted caption (no LLM)."""
        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=True
        )
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.post(f"/api/carousels/{project_id}/caption")
        assert resp.status_code == 200
        body = resp.json()
        assert body["caption"] == FIXTURE_CAPTION
        assert body["hashtags"] == []

    @pytest.mark.asyncio
    async def test_publish_instagram_returns_published(
        self, pub_env: PubEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: publish/instagram returns the stubbed published result."""
        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=True
        )
        _stub_artifact_health(monkeypatch)
        stub = _override_publisher(pub_env)
        try:
            async with pub_env.client_for(pub_env.owner) as client:
                resp = await client.post(
                    f"/api/carousels/{project_id}/publish/instagram",
                    json={"caption": FIXTURE_CAPTION},
                )
        finally:
            _reset_publisher()
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "published"
        assert body["ig_post_id"] == STUB_IG_POST_ID
        # The route built public image URLs from the pinned base URL.
        assert stub.calls
        _caption, urls = stub.calls[0]
        assert all(url.startswith(f"{PUBLIC_BASE_URL}/") for url in urls)

    @pytest.mark.asyncio
    async def test_publish_instagram_forbidden_when_not_approved(
        self, pub_env: PubEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: publish/instagram is forbidden when not approved for release."""
        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=False
        )
        _stub_artifact_health(monkeypatch)
        stub = _override_publisher(pub_env)
        try:
            async with pub_env.client_for(pub_env.owner) as client:
                resp = await client.post(
                    f"/api/carousels/{project_id}/publish/instagram",
                    json={"caption": FIXTURE_CAPTION},
                )
        finally:
            _reset_publisher()
        assert resp.status_code == 403


# ==============================================================================
# AE-0204: caption + LinkedIn are served from the canonical distribution home
# (blog_posts.distribution), NOT the embedded carousel columns.
# ==============================================================================
class TestDistributionCanonicalHome:
    """The 3 distribution fields source from ``blog_posts.distribution`` (AE-0204)."""

    @pytest.mark.asyncio
    async def test_dual_write_populates_canonical_home(
        self, pub_env: PubEnv
    ) -> None:
        """Scenario: the carousel dual-write mirrors caption + LinkedIn into the home.

        Given a carousel with caption + LinkedIn posts, the carousel-blog write
        chokepoint mirrors all three into the canonical ``blog_posts.distribution``
        column on the ``origin='carousel'`` row — byte-identical to the embedded
        values — so the row becomes the source of truth every reader consumes.
        """
        from sqlalchemy import select

        from rag_backend.domain.constants.blog_post import BlogPostOrigin
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.distribution_home import (
            DISTRIBUTION_CAPTION_KEY,
            DISTRIBUTION_LINKEDIN_POST_EN_KEY,
            DISTRIBUTION_LINKEDIN_POST_PT_KEY,
        )
        from rag_backend.infrastructure.database.models import BlogPostModel

        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=False
        )

        from uuid import UUID

        from rag_backend.infrastructure.database.carousel_repository import (
            PostgresCarouselRepository,
        )

        session_maker = get_session_maker()
        # A writer (refine_copy / editorial_distribution_pack pattern): load the
        # entity, set the LinkedIn posts on it, and persist via the repository so
        # the dual-write chokepoint mirrors them into the canonical home.
        async with session_maker() as session:
            repo = PostgresCarouselRepository(session)
            project = await repo.get_project_by_id(UUID(project_id))
            assert project is not None
            project.linkedin_post_pt = _FIXTURE_LINKEDIN_PT
            project.linkedin_post_en = _FIXTURE_LINKEDIN_EN
            await repo.update_project(project)

        async with session_maker() as session:
            row = (
                await session.execute(
                    select(BlogPostModel).where(
                        BlogPostModel.project_id == project_id,
                        BlogPostModel.origin == BlogPostOrigin.CAROUSEL.value,
                    )
                )
            ).scalars().one()
            assert row.distribution[DISTRIBUTION_CAPTION_KEY] == FIXTURE_CAPTION
            assert (
                row.distribution[DISTRIBUTION_LINKEDIN_POST_PT_KEY]
                == _FIXTURE_LINKEDIN_PT
            )
            assert (
                row.distribution[DISTRIBUTION_LINKEDIN_POST_EN_KEY]
                == _FIXTURE_LINKEDIN_EN
            )

    @pytest.mark.asyncio
    async def test_caption_route_reads_from_home_not_embedded_column(
        self, pub_env: PubEnv
    ) -> None:
        """Rule-fires (AE-0180): the caption read sources the HOME, not the column.

        Seed a carousel, then DESYNC the embedded ``carousel_projects.caption``
        column to a poison value while leaving the canonical
        ``blog_posts.distribution`` home holding the real caption. The caption route
        must still return the canonical caption — proving no reader sources the
        field from the embedded column. This test FAILS if a reader regresses to the
        embedded column.
        """
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=True
        )

        # Desync: poison the embedded column ONLY (the home keeps FIXTURE_CAPTION).
        session_maker = get_session_maker()
        async with session_maker() as session:
            model = await session.get(CarouselProjectModel, project_id)
            assert model is not None
            model.caption = _POISON_CAPTION
            await session.commit()

        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.post(f"/api/carousels/{project_id}/caption")
        assert resp.status_code == 200
        # The canonical home wins — the poison embedded value is never read.
        assert resp.json()["caption"] == FIXTURE_CAPTION
        assert resp.json()["caption"] != _POISON_CAPTION


# ==============================================================================
# Carousel publish flow (approval -> is_public release) — CURRENT behavior
# ==============================================================================
class TestCarouselPublishFlow:
    """POST /carousels/{id}/publish sets is_public=True (AE-0128 diff target)."""

    @pytest.mark.asyncio
    async def test_publish_sets_is_public(
        self, pub_env: PubEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: publish marks the carousel public (current release flow)."""
        project_id = await pub_env.seed_carousel(
            is_public=False, approved_for_publish=True
        )
        _stub_artifact_health(monkeypatch)
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.post(f"/api/carousels/{project_id}/publish")
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_public"] is True
        assert body["current_phase"] == "published"

    @pytest.mark.asyncio
    async def test_publish_forbidden_when_not_approved(
        self, pub_env: PubEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: publish is forbidden when not approved for release."""
        project_id = await pub_env.seed_carousel(
            is_public=False, approved_for_publish=False
        )
        _stub_artifact_health(monkeypatch)
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.post(f"/api/carousels/{project_id}/publish")
        assert resp.status_code == 403


# ==============================================================================
# Calendar / board / analytics behavior
# ==============================================================================
class TestCalendarBoardAnalytics:
    """GET /content-calendar + /workflow-board + /editorial-analytics."""

    @pytest.mark.asyncio
    async def test_calendar_includes_scheduled_post(self, pub_env: PubEnv) -> None:
        """Scenario: content-calendar lists a scheduled blog post."""
        await pub_env.seed_calendar_blog_post()
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.get(
                "/api/content-calendar",
                params={
                    "start": "2026-06-01T00:00:00+00:00",
                    "end": "2026-06-30T00:00:00+00:00",
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        titles = [item["title"] for item in body["items"]]
        assert CALENDAR_BLOG_TITLE in titles

    @pytest.mark.asyncio
    async def test_board_groups_project_by_phase(self, pub_env: PubEnv) -> None:
        """Scenario: workflow-board groups the carousel into its phase column."""
        await pub_env.seed_carousel(is_public=False, approved_for_publish=True)
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.get("/api/workflow-board")
        assert resp.status_code == 200
        columns = {col["phase"]: col for col in resp.json()["columns"]}
        content_cards = columns[PHASE_CONTENT]["cards"]
        assert content_cards
        assert content_cards[0]["topic"] == "Fixture topic"

    @pytest.mark.asyncio
    async def test_analytics_counts_blog_posts(self, pub_env: PubEnv) -> None:
        """Scenario: editorial-analytics aggregates blog-post counts."""
        async with pub_env.client_for(pub_env.owner) as client:
            await _create_blog_post(client)
            resp = await client.get("/api/editorial-analytics")
        assert resp.status_code == 200
        summary = resp.json()["summary"]
        assert summary["total_posts"] == 1
        assert summary["draft_count"] == 1


# ==============================================================================
# Golden snapshots — deterministic byte-identical baselines (AE-0128/0129/0131)
# ==============================================================================
class TestPublishingSnapshots:
    """Blog/publish/distribution/calendar/board/analytics golden snapshots."""

    async def _check(self, name: str, resp: Response, *, update: bool) -> None:
        if update:
            publishing_snapshot.write_snapshot(name, resp)
            return
        publishing_snapshot.assert_matches_snapshot(name, resp)

    @pytest.mark.asyncio
    async def test_snapshot_blog_post_create(
        self, pub_env: PubEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /blog-posts (201)."""
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await _create_blog_post(client)
        await self._check("blog_post_create", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_blog_post_get(
        self, pub_env: PubEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /blog-posts/{id} (200)."""
        async with pub_env.client_for(pub_env.owner) as client:
            created = await _create_blog_post(client)
            resp = await client.get(f"/api/blog-posts/{created.json()['id']}")
        await self._check("blog_post_get", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_blog_post_list(
        self, pub_env: PubEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /blog-posts (200 list)."""
        async with pub_env.client_for(pub_env.owner) as client:
            await _create_blog_post(client)
            resp = await client.get("/api/blog-posts")
        await self._check("blog_post_list", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_blog_post_update(
        self, pub_env: PubEnv, snapshot_update: bool
    ) -> None:
        """Golden: PUT /blog-posts/{id} (200)."""
        async with pub_env.client_for(pub_env.owner) as client:
            created = await _create_blog_post(client)
            resp = await client.put(
                f"/api/blog-posts/{created.json()['id']}",
                json={"excerpt": "Updated excerpt."},
                headers={"If-Match": "1"},
            )
        await self._check("blog_post_update", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_blog_post_delete(
        self, pub_env: PubEnv, snapshot_update: bool
    ) -> None:
        """Golden: DELETE /blog-posts/{id} (204)."""
        async with pub_env.client_for(pub_env.owner) as client:
            created = await _create_blog_post(client)
            resp = await client.delete(f"/api/blog-posts/{created.json()['id']}")
        await self._check("blog_post_delete", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_carousel_blog(
        self, pub_env: PubEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /carousels/{id}/blog (200)."""
        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=False
        )
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/blog")
        await self._check("carousel_blog", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_carousel_blog_i18n(
        self, pub_env: PubEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /carousels/{id}/blog/{lang} (200)."""
        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=False
        )
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/blog/en")
        await self._check("carousel_blog_i18n_en", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_caption(
        self, pub_env: PubEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /carousels/{id}/caption (200)."""
        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=True
        )
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.post(f"/api/carousels/{project_id}/caption")
        await self._check("caption", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_publish_instagram(
        self,
        pub_env: PubEnv,
        snapshot_update: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Golden: POST /carousels/{id}/publish/instagram (200, stubbed)."""
        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=True
        )
        _stub_artifact_health(monkeypatch)
        _override_publisher(pub_env)
        try:
            async with pub_env.client_for(pub_env.owner) as client:
                resp = await client.post(
                    f"/api/carousels/{project_id}/publish/instagram",
                    json={"caption": FIXTURE_CAPTION},
                )
        finally:
            _reset_publisher()
        await self._check("publish_instagram", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_carousel_publish(
        self,
        pub_env: PubEnv,
        snapshot_update: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Golden: POST /carousels/{id}/publish (200) — sets is_public=True.

        This is the CURRENT approval->release flow AE-0128's release command
        must diff to zero against.
        """
        project_id = await pub_env.seed_carousel(
            is_public=False, approved_for_publish=True
        )
        _stub_artifact_health(monkeypatch)
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.post(f"/api/carousels/{project_id}/publish")
        await self._check("carousel_publish", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_content_calendar(
        self, pub_env: PubEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /content-calendar (200)."""
        await pub_env.seed_calendar_blog_post()
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.get(
                "/api/content-calendar",
                params={
                    "start": "2026-06-01T00:00:00+00:00",
                    "end": "2026-06-30T00:00:00+00:00",
                },
            )
        await self._check("content_calendar", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_workflow_board(
        self, pub_env: PubEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /workflow-board (200)."""
        await pub_env.seed_carousel(is_public=False, approved_for_publish=True)
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.get("/api/workflow-board")
        await self._check("workflow_board", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_editorial_analytics(
        self, pub_env: PubEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /editorial-analytics (200)."""
        async with pub_env.client_for(pub_env.owner) as client:
            await _create_blog_post(client)
            resp = await client.get("/api/editorial-analytics")
        await self._check("editorial_analytics", resp, update=snapshot_update)


# ==============================================================================
# Falsifiability guard — the snapshot diff is not a no-op
# ==============================================================================
class TestSafetyNetIsFalsifiable:
    """Prove the byte-identical snapshot diff rejects a mutated payload."""

    @pytest.mark.asyncio
    async def test_snapshot_diff_detects_mutation(self, pub_env: PubEnv) -> None:
        """Scenario: the snapshot diff is non-empty for a mutated response."""
        project_id = await pub_env.seed_carousel(
            is_public=True, approved_for_publish=False
        )
        async with pub_env.client_for(pub_env.owner) as client:
            resp = await client.get(f"/api/carousels/{project_id}/blog")
        # Live response matches the committed baseline.
        assert publishing_snapshot.diff_snapshot("carousel_blog", resp) == []
        # A mutated copy of the SAME response must be rejected by the same check.
        snapshot = publishing_snapshot.build_snapshot(resp)
        mutated = publishing_snapshot.load_snapshot("carousel_blog")
        assert mutated == snapshot
        body = mutated["body"]
        assert isinstance(body, dict)
        body["markdown"] = "MUTATED"
        assert mutated != snapshot
