"""Blog generation entry points end to end (AE-0425, ADR-0025).

Feature: backend/tests/features/blog_generate_ae0425.feature
The run uses the real routes, the real tracked runner and the real
lease-fenced SQL store; only the LLM writer, the voice scorer and the image
provider are fakes.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.api.routes import blog_generate_support
from rag_backend.application.services.blog import blog_generation_runner as runner
from rag_backend.application.services.blog.blog_generation_service import (
    BlogGenerationDeps,
    BlogGenerationService,
    GenerationTimings,
)
from rag_backend.application.services.blog.blog_quality_gate import (
    BlogQualityGate,
    QualityGateDeps,
)
from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.domain.models import UserRole
from rag_backend.domain.models.blog_generation import (
    DraftArticle,
    DraftSection,
    WriterBrief,
)
from rag_backend.domain.models.persona import PersonaProfile
from tests.blog_generation_fakes import (
    FAIL_IMAGE_MARKER,
    FakeImageGenerator,
    FakeScorer,
    FakeWriter,
    article,
    english_gate,
    image_batch,
    writer_failure,
)
from tests.blog_v2_support import v2_content
from tests.integration.conftest import auth_headers_for, create_test_user

FROM_CAROUSEL = "/api/blog-posts/from-carousel"
GENERATE = "/api/blog-posts/generate"
POSTS = "/api/blog-posts"


@pytest.fixture(autouse=True)
def _no_langfuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate from any Langfuse client an earlier test configured (its flush
    to an unreachable host would eat the run's timeout)."""
    from contextlib import nullcontext

    from rag_backend.application.services.blog import (
        blog_generation_service,
        blog_image_batch,
    )

    for module in (blog_generation_service, blog_image_batch):
        monkeypatch.setattr(
            module,
            "blog_phase_trace",
            lambda _scope, **_kwargs: nullcontext(MagicMock()),
        )
    # The editor's single-image service (AE-0424) traces with its own helper.
    from rag_backend.application.services.blog import blog_image_service as _single

    monkeypatch.setattr(_single, "blog_ai_propagate", lambda *_a: nullcontext())


class _Harness:
    """What the fake service factory saw and how the next run behaves."""

    def __init__(self, images_dir: Path) -> None:
        self.images_dir = images_dir
        self.writer = FakeWriter(draft_article=article(9))
        self.generator = FakeImageGenerator()
        self.personas: list[PersonaProfile] = []

    def build(self, persona: PersonaProfile, user_id: str) -> BlogGenerationService:
        from rag_backend.bootstrap.blog_generation_store import (
            RunOwner,
            SlotWriteGenerationStore,
        )
        from rag_backend.infrastructure.database.config import get_session_maker

        self.personas.append(persona)
        gate = BlogQualityGate(QualityGateDeps(self.writer, FakeScorer(scores=[80.0])))
        return BlogGenerationService(
            BlogGenerationDeps(
                writer=self.writer,
                gate=gate,
                english=english_gate(gate),
                images=image_batch(self.images_dir, self.generator),
                store=SlotWriteGenerationStore(
                    get_session_maker(), RunOwner(user_id=user_id, image_cap=30)
                ),
                timings=GenerationTimings(
                    text_timeout_seconds=10, image_wave_seconds=10, heartbeat_seconds=5
                ),
            )
        )


@pytest.fixture
async def harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Harness:
    from rag_backend.api.routes import blog_post_images
    from rag_backend.application.services.asset_cdn_service import AssetCdnService
    from rag_backend.application.services.blog.blog_image_store import BlogImageStore

    images = tmp_path / "blog-images"
    built = _Harness(images)
    monkeypatch.setattr(blog_generate_support, "build_generation_service", built.build)
    # The editor's (AE-0424) store + serving route is the only image path.
    store = BlogImageStore(root=images, cdn=AssetCdnService())
    monkeypatch.setattr(blog_post_images, "blog_images_store", lambda: store)
    return built


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ae0425-api.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    limiter.reset()
    editor = await create_test_user("editor@ae0425.test", UserRole.EDITOR)
    transport = ASGITransport(app=create_app())
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=auth_headers_for(editor)
    ) as ac:
        ac.headers["X-Test-User"] = str(editor.id)
        yield ac
    await runner.cancel_blog_generation_tasks()
    db_config.c_engine = None
    await close_db()
    await engine.dispose()


async def _project(
    client: AsyncClient, *, is_public: bool = False, slide_count: int | None = 9
) -> str:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

    async with get_session_maker()() as session:
        project = CarouselProjectModel(
            topic="Agentes de IA",
            audience="devs",
            niche="IA",
            is_public=is_public,
            owner_id=client.headers["X-Test-User"],
            content_mode="pov",
            slide_count=slide_count,
        )
        session.add(project)
        await session.commit()
        return str(project.id)


async def _blog_row(project_id: str, status: str, hidden: bool = False) -> str:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

    metadata = (
        {"hidden_bad_post": {"at": "2026-10-18", "reason": "old pipeline"}}
        if hidden
        else {}
    )
    async with get_session_maker()() as session:
        post = BlogPostModel.from_entity({
            "project_id": project_id,
            "origin": BlogPostOrigin.CAROUSEL.value,
            "title": "Old",
            "slug": f"old-{uuid4()}",
            "status": status,
            "content": v2_content(),
            "ai_generation_metadata": metadata,
        })
        session.add(post)
        await session.commit()
        return str(post.id)


async def _settled(client: AsyncClient, post_id: str) -> dict:
    await asyncio.gather(*runner.running_blog_generation_tasks())
    response = await client.get(f"{POSTS}/{post_id}")
    assert response.status_code == 200, response.text
    return response.json()


async def test_from_carousel_creates_a_draft_and_completes(
    client: AsyncClient, harness: _Harness
) -> None:
    # Scenario: From-carousel always creates a draft
    # Scenario: Section and image count follow the carousel slide count
    project_id = await _project(client, is_public=True)
    response = await client.post(FROM_CAROUSEL, json={"project_id": project_id})
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["generation"] == {"status": "in_progress", "attempt": 1, "warnings": []}
    post = await _settled(client, body["id"])
    assert post["status"] == BlogPostStatus.DRAFT.value
    assert post["origin"] == BlogPostOrigin.CAROUSEL.value
    generation = post["ai_generation_metadata"]["generation"]
    assert generation["status"] == "complete"
    assert generation["image_count"] == 10
    assert generation["image_slots"] == 10
    assert len(post["content"]["sections"]) == 9
    assert post["featured_image_url"] == post["content"]["cover"]["url"]
    assert (
        post["ai_generation_metadata"]["voice_score"]
        == post["content"]["quality"]["voice_score"]
    )
    assert harness.writer.drafts[0].section_count == 9
    # The cover is served from the blog-images store to its author.
    image = await client.get(post["content"]["cover"]["url"])
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/jpeg"


async def test_from_carousel_404s_an_unknown_project(
    client: AsyncClient, harness: _Harness
) -> None:
    # Scenario: From-carousel 404s an unknown project
    response = await client.post(FROM_CAROUSEL, json={"project_id": str(uuid4())})
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("status", "hidden"),
    [("draft", False), ("approved", False), ("published", False), ("draft", True)],
)
async def test_from_carousel_409s_for_any_existing_row(
    client: AsyncClient, harness: _Harness, status: str, hidden: bool
) -> None:
    # Scenario: From-carousel 409s when a live blog row already exists
    project_id = await _project(client)
    existing = await _blog_row(project_id, status, hidden)
    response = await client.post(FROM_CAROUSEL, json={"project_id": project_id})
    assert response.status_code == 409
    assert response.json() == {
        "code": "blog_post_exists_for_project",
        "post_id": existing,
    }
    assert harness.personas == []


async def test_a_private_carousel_warns(client: AsyncClient, harness: _Harness) -> None:
    # Scenario: A private source carousel warns that the post will not be public
    project_id = await _project(client, is_public=False)
    response = await client.post(FROM_CAROUSEL, json={"project_id": project_id})
    assert response.json()["generation"]["warnings"] == ["carousel_private"]
    post = await _settled(client, response.json()["id"])
    assert post["ai_generation_metadata"]["generation"]["warnings"] == [
        "carousel_private"
    ]


async def test_standalone_generation_creates_a_draft(
    client: AsyncClient, harness: _Harness
) -> None:
    # Scenario: Standalone generation creates a draft from a topic
    # Scenario: Standalone generation uses the content-mode default
    harness.writer.draft_article = article(7)
    response = await client.post(
        GENERATE,
        json={
            "topic": "Por que eu parei de usar copilots",
            "source_urls": ["https://example.com/x"],
        },
    )
    assert response.status_code == 202, response.text
    post = await _settled(client, response.json()["id"])
    assert post["project_id"] is None
    assert post["origin"] == BlogPostOrigin.STANDALONE.value
    assert post["status"] == "draft"
    assert len(post["content"]["sections"]) == 7
    assert post["title"] == "Título do artigo"
    assert harness.writer.drafts[0].source_urls == ("https://example.com/x",)


async def test_an_llm_failure_keeps_the_draft_and_the_owner_retries(
    client: AsyncClient, harness: _Harness
) -> None:
    # Scenario: An LLM failure leaves the draft with status failed
    # Scenario: The owner can retry an interrupted generation on the same row
    harness.writer.draft_error = writer_failure()
    harness.writer.draft_article = article(7)
    response = await client.post(GENERATE, json={"topic": "Um tema qualquer"})
    post_id = response.json()["id"]
    failed = await _settled(client, post_id)
    assert failed["ai_generation_metadata"]["generation"]["status"] == "failed"
    assert failed["ai_generation_metadata"]["generation"]["recoverable"] is True
    assert failed["content"]["sections"] == []

    harness.writer.draft_error = None
    retry = await client.post(f"{POSTS}/{post_id}/generation/retry")
    assert retry.status_code == 202, retry.text
    assert retry.json()["generation"]["attempt"] == 2
    done = await _settled(client, post_id)
    assert done["ai_generation_metadata"]["generation"]["status"] == "complete"
    listing = await client.get(POSTS)
    assert [item["id"] for item in listing.json()["items"]].count(post_id) == 1


async def test_retry_is_refused_unless_the_run_failed(
    client: AsyncClient, harness: _Harness
) -> None:
    harness.writer.draft_article = article(7)
    response = await client.post(GENERATE, json={"topic": "Outro tema"})
    post_id = response.json()["id"]
    await _settled(client, post_id)
    retry = await client.post(f"{POSTS}/{post_id}/generation/retry")
    assert retry.status_code == 409
    assert retry.json()["detail"] == "blog_generation_not_retryable"


@dataclass
class _GatedWriter(FakeWriter):
    gate: asyncio.Event = field(default_factory=asyncio.Event)

    async def draft(self, brief: WriterBrief) -> DraftArticle:
        await self.gate.wait()
        return await super().draft(brief)


async def test_retry_while_in_progress_is_refused(
    client: AsyncClient, harness: _Harness
) -> None:
    writer = _GatedWriter(draft_article=article(7))
    harness.writer = writer
    response = await client.post(GENERATE, json={"topic": "Tema lento"})
    post_id = response.json()["id"]
    retry = await client.post(f"{POSTS}/{post_id}/generation/retry")
    assert retry.status_code == 409
    assert retry.json()["detail"] == "blog_generation_in_progress"
    writer.gate.set()
    # Let the run finish: teardown cancelling it mid-query orphans a connection.
    await _settled(client, post_id)


async def test_a_partial_run_retries_only_its_missing_images(
    client: AsyncClient, harness: _Harness
) -> None:
    # Review fix 3: the retry of a post whose article exists never rewrites it.
    draft = article(7)
    pt = list(draft.sections)
    pt[3] = DraftSection(heading=FAIL_IMAGE_MARKER, body_md=pt[3].body_md)
    harness.writer.draft_article = DraftArticle(
        draft.title, tuple(pt), draft.en_title, draft.en_sections
    )
    response = await client.post(GENERATE, json={"topic": "Tema parcial"})
    post_id = response.json()["id"]
    partial = await _settled(client, post_id)
    generation = partial["ai_generation_metadata"]["generation"]
    assert generation["status"] == "partial"
    # Reserved before the spend: all 8 slots (the failed one may be billed).
    assert partial["ai_generation_metadata"]["blog_image_generations"] == 8
    bodies = [s["body_md"] for s in partial["content"]["sections"]]

    harness.generator.honor_marker = False
    retry = await client.post(f"{POSTS}/{post_id}/generation/retry")
    assert retry.status_code == 202, retry.text
    done = await _settled(client, post_id)
    generation = done["ai_generation_metadata"]["generation"]
    assert generation["status"] == "complete"
    assert generation["mode"] == "images_only"
    assert generation["image_slots"] == 1
    # Counted on AE-0424's per-post cap across attempts.
    assert done["ai_generation_metadata"]["blog_image_generations"] == 9
    assert len(harness.writer.drafts) == 1  # the writer ran once, never again
    assert [s["body_md"] for s in done["content"]["sections"]] == bodies
    assert done["content"]["sections"][3]["image"] is not None


async def test_retry_of_an_unparseable_row_reruns_the_writer(
    client: AsyncClient, harness: _Harness
) -> None:
    # AE-0428 review: a row that does not parse is "no article" (never a 500).
    from sqlalchemy import update

    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

    harness.writer.draft_error = writer_failure()
    response = await client.post(GENERATE, json={"topic": "Tema quebrado"})
    post_id = response.json()["id"]
    await _settled(client, post_id)
    async with get_session_maker()() as session:
        await session.execute(
            update(BlogPostModel)
            .where(BlogPostModel.id == post_id)
            .values(content={"markdown": "# legado"})
        )
        await session.commit()
    harness.writer.draft_error = None
    harness.writer.draft_article = article(7)
    retry = await client.post(f"{POSTS}/{post_id}/generation/retry")
    assert retry.status_code == 202, retry.text
    done = await _settled(client, post_id)
    assert len(harness.writer.drafts) == 2  # the full writer ran again
    # Review B: the unparseable row is REPLACED by the new v2 document (a
    # full-document write), so the paid retry is not a dead end.
    assert done["ai_generation_metadata"]["generation"]["status"] == "complete"
    assert done["content"]["schema"] == "blog.v2"
    assert len(done["content"]["sections"]) == 7
    assert done["content"]["cover"] is not None


async def test_generated_images_are_served_by_the_editor_route(
    client: AsyncClient, harness: _Harness
) -> None:
    # Review fix 4: one image store/route (AE-0424's): uuid4 names, public.
    harness.writer.draft_article = article(7)
    response = await client.post(GENERATE, json={"topic": "Tema servido"})
    post = await _settled(client, response.json()["id"])
    image = await client.get(post["content"]["cover"]["url"])
    assert image.status_code == 200
    missing = await client.get(f"/api/blog-images/{post['id']}/{uuid4()}.jpg")
    assert missing.status_code == 404


async def test_generation_routes_are_rate_limited(
    client: AsyncClient, harness: _Harness
) -> None:
    # Scenario: Image generation is rate limited and cost-capped
    harness.writer.draft_error = writer_failure()
    statuses = [
        (await client.post(GENERATE, json={"topic": f"Tema {index}"})).status_code
        for index in range(11)
    ]
    assert statuses[:10] == [202] * 10
    assert statuses[10] == 429
