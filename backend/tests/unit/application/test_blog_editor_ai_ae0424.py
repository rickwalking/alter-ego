"""Unit tests of the blog editor AI services (AE-0424, ADR-0025).

Feature: backend/tests/features/blog_post_ai_contract_ae0424.feature
Image persistence (canonical URL only), PT -> EN translation and the
persona-voice section rewrite.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.asset_cdn_service import AssetCdnService
from rag_backend.application.services.blog.blog_image_service import (
    BlogImageError,
    BlogImageRequest,
    BlogImageService,
    BlogImageStore,
    default_scene,
)
from rag_backend.application.services.blog.blog_translation_service import (
    BlogTranslationError,
    BlogTranslationService,
)
from rag_backend.application.services.blog_post_ai_service import (
    BlogPostAIService,
    _RewriteInput,
)
from rag_backend.domain.constants.blog_editor import (
    ERR_BLOG_IMAGE_GENERATION_FAILED,
    ERR_BLOG_IMAGE_PERSIST_FAILED,
    ERR_BLOG_PERSONA_REQUIRED,
    ERR_BLOG_REWRITE_EMPTY,
)
from rag_backend.domain.models.blog_document import BlogImage, parse_blog_content
from tests.blog_v2_support import v2_content, v2_section

POST_ID = "11111111-1111-4111-8111-111111111111"
PROVIDER_URL = "https://provider.example/tmp/abc.png"
SEC_2 = "sec_00000000-0000-4000-8000-000000000002"


@pytest.fixture(autouse=True)
def _no_langfuse() -> Iterator[None]:
    context = MagicMock(__enter__=MagicMock(), __exit__=MagicMock(return_value=False))
    targets = (
        "rag_backend.application.services.blog.blog_image_service.blog_ai_propagate",
        "rag_backend.application.services.blog.blog_translation_service.blog_ai_propagate",
        "rag_backend.application.services.blog_post_ai_service.blog_ai_propagate",
    )
    with patch(targets[0], return_value=context), patch(
        targets[1], return_value=context
    ), patch(targets[2], return_value=context):
        yield


class _WritingProvider:
    """Writes bytes to the requested path and returns a provider URL."""

    def __init__(self, payload: bytes = b"jpeg") -> None:
        self.payload = payload
        self.prompts: list[str] = []

    async def generate_image(self, prompt: str, output_path: str) -> str:
        self.prompts.append(prompt)
        if self.payload:
            Path(output_path).write_bytes(self.payload)
        return PROVIDER_URL


def _store(tmp_path: Path, cdn: AssetCdnService | None = None) -> BlogImageStore:
    return BlogImageStore(root=tmp_path / "blog-images", cdn=cdn or AssetCdnService())


def _request(scene: str = "Um farol na costa") -> BlogImageRequest:
    return BlogImageRequest(post_id=POST_ID, scene=scene, alt="O que aconteceu")


class TestBlogImageService:
    # Scenario: Generated images are persisted before they are stored
    async def test_bytes_are_persisted_and_canonical_url_stored(
        self, tmp_path: Path
    ) -> None:
        provider = _WritingProvider()
        image = await BlogImageService(provider, _store(tmp_path)).generate(_request())
        assert image.url.startswith(f"/api/blog-images/{POST_ID}/")
        assert image.url.endswith(".jpg")
        assert PROVIDER_URL not in image.model_dump_json()
        stored = tmp_path / "blog-images" / POST_ID / image.url.rsplit("/", 1)[1]
        assert stored.read_bytes() == b"jpeg"
        assert image.alt == "O que aconteceu"
        assert image.model == "gpt-image-2"
        assert image.source == "generated"
        assert image.prompt == "Um farol na costa"

    async def test_template_forbids_text_and_wraps_the_scene(
        self, tmp_path: Path
    ) -> None:
        provider = _WritingProvider()
        await BlogImageService(provider, _store(tmp_path)).generate(_request())
        prompt = provider.prompts[0]
        assert "no text, no words, no letters, no numbers" in prompt
        assert "Um farol na costa" in prompt

    async def test_image_prompt_sanitizer_is_applied(self, tmp_path: Path) -> None:
        provider = _WritingProvider()
        image = await BlogImageService(provider, _store(tmp_path)).generate(
            _request("Elon Musk on stage")
        )
        assert "Musk" not in provider.prompts[0]
        assert "Musk" not in (image.prompt or "")

    async def test_cdn_url_when_enabled(self, tmp_path: Path) -> None:
        cdn = AssetCdnService(cdn_base_url="https://cdn.example", enabled=True)
        image = await BlogImageService(_WritingProvider(), _store(tmp_path, cdn)).generate(
            _request()
        )
        assert image.url.startswith(f"https://cdn.example/blog-images/{POST_ID}/")

    # Scenario: A failed image generation shows a visible retry (backend: 502 code)
    async def test_provider_failure_raises_generation_failed(
        self, tmp_path: Path
    ) -> None:
        provider = MagicMock()
        provider.generate_image = AsyncMock(side_effect=RuntimeError("boom"))
        with pytest.raises(BlogImageError) as exc:
            await BlogImageService(provider, _store(tmp_path)).generate(_request())
        assert exc.value.code == ERR_BLOG_IMAGE_GENERATION_FAILED

    async def test_missing_file_is_a_persist_failure(self, tmp_path: Path) -> None:
        with pytest.raises(BlogImageError) as exc:
            await BlogImageService(_WritingProvider(b""), _store(tmp_path)).generate(
                _request()
            )
        assert exc.value.code == ERR_BLOG_IMAGE_PERSIST_FAILED

    async def test_no_provider_is_a_generation_failure(self, tmp_path: Path) -> None:
        with pytest.raises(BlogImageError) as exc:
            await BlogImageService(None, _store(tmp_path)).generate(_request())
        assert exc.value.code == ERR_BLOG_IMAGE_GENERATION_FAILED

    def test_store_file_lookup(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        path = store.new_path(POST_ID)
        assert store.file_for(POST_ID, path.name) is None
        path.write_bytes(b"x")
        assert store.file_for(POST_ID, path.name) == path


class TestDefaultScene:
    def test_heading_and_excerpt(self) -> None:
        assert default_scene("Título", "Corpo\n\ncom   espaço") == (
            "Título. Corpo com espaço"
        )

    def test_no_heading(self) -> None:
        assert default_scene(None, "Corpo") == "Corpo"

    def test_excerpt_is_bounded(self) -> None:
        assert len(default_scene(None, "a" * 5000)) == 600


def _llm(answers: list[str]) -> MagicMock:
    llm = MagicMock()
    llm.generate = AsyncMock(side_effect=answers)
    return llm


def _pt_document() -> object:
    content = v2_content("Corpo um", "Um")
    image = {"url": "https://cdn.example/a.jpg", "alt": "Arte"}
    content["sections"] = [
        {**v2_section("Corpo um", "Um"), "image": image},
        v2_section("", None, SEC_2),
    ]
    content["cover"] = image
    return parse_blog_content(content)


class TestBlogTranslationService:
    # Scenario: A missing EN translation is read-only with a generate action
    async def test_translates_sections_keeping_images_and_cover(self) -> None:
        answer = json.dumps({"heading": "One", "body_md": "Body one"})
        service = BlogTranslationService(_llm([f"```json\n{answer}\n```"]))
        english = await service.translate(POST_ID, _pt_document())
        first, empty = english.sections
        assert (first.heading, first.body_md) == ("One", "Body one")
        assert first.image is not None and first.image.url.endswith("a.jpg")
        assert first.id != "sec_00000000-0000-4000-8000-000000000001"
        assert empty.body_md == ""
        assert empty.id != SEC_2
        assert english.cover is not None
        assert english.quality is None

    async def test_headingless_section_stays_headingless(self) -> None:
        answer = json.dumps({"heading": "Invented", "body_md": "Body"})
        document = parse_blog_content(v2_content("Corpo", None))
        english = await BlogTranslationService(_llm([answer])).translate(
            POST_ID, document
        )
        assert english.sections[0].heading is None

    @pytest.mark.parametrize(
        "answer",
        ["not json", json.dumps({"heading": "x"}), json.dumps(["x"]), "{\"body_md\": \" \"}"],
    )
    async def test_bad_answer_fails_the_translation(self, answer: str) -> None:
        document = parse_blog_content(v2_content("Corpo", "Um"))
        with pytest.raises(BlogTranslationError):
            await BlogTranslationService(_llm([answer])).translate(POST_ID, document)

    async def test_llm_error_fails_the_translation(self) -> None:
        llm = MagicMock()
        llm.generate = AsyncMock(side_effect=TimeoutError())
        document = parse_blog_content(v2_content("Corpo", "Um"))
        with pytest.raises(BlogTranslationError):
            await BlogTranslationService(llm).translate(POST_ID, document)

    async def test_non_string_heading_becomes_null(self) -> None:
        answer = json.dumps({"heading": 3, "body_md": "Body"})
        document = parse_blog_content(v2_content("Corpo", "Um"))
        english = await BlogTranslationService(_llm([answer])).translate(
            POST_ID, document
        )
        assert english.sections[0].heading is None


def _ai_service() -> BlogPostAIService:
    llm = MagicMock()
    llm.chat_model = MagicMock()
    return BlogPostAIService(llm_service=llm, image_service=None, output_dir=Path("."))


def _db(persona: object | None = None, project: object | None = None) -> MagicMock:
    db = MagicMock()
    db.get = AsyncMock(side_effect=lambda model, _id: project if "Carousel" in model.__name__ else persona)
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=persona)
    db.execute = AsyncMock(return_value=result)
    return db


class TestRewriteSection:
    def _persona_model(self) -> MagicMock:
        model = MagicMock()
        model.to_entity = MagicMock(return_value=MagicMock(name="persona"))
        return model

    async def _run(self, db: MagicMock, rewrite: str, **fields: object) -> str:
        with patch(
            "rag_backend.application.services.blog_post_ai_service.PersonaAgent"
        ) as agent_cls:
            agent_cls.return_value.enforce = AsyncMock(return_value=rewrite)
            return await _ai_service().rewrite_section(
                _RewriteInput(db=db, body_md="Texto genérico", **fields)
            )

    # Scenario: Rewriting a section replaces only that section's body
    async def test_explicit_persona_is_used(self) -> None:
        db = _db(persona=self._persona_model())
        text = await self._run(db, "```\nTexto na minha voz\n```", persona_id="p1")
        assert text == "Texto na minha voz"
        db.execute.assert_not_awaited()

    # Scenario: Rewriting a section without a persona uses the default persona
    async def test_project_persona_is_the_default(self) -> None:
        project = MagicMock(persona_id="p-project")
        db = _db(persona=self._persona_model(), project=project)
        assert await self._run(db, "Voz", project_id="proj") == "Voz"
        db.execute.assert_not_awaited()

    async def test_first_persona_when_nothing_bound(self) -> None:
        db = _db(persona=self._persona_model(), project=MagicMock(persona_id=None))
        assert await self._run(db, "Voz", project_id="proj") == "Voz"
        db.execute.assert_awaited_once()

    async def test_no_persona_at_all_is_rejected(self) -> None:
        with pytest.raises(ValueError, match=ERR_BLOG_PERSONA_REQUIRED):
            await self._run(_db(persona=None), "Voz")

    async def test_empty_rewrite_is_rejected(self) -> None:
        with pytest.raises(ValueError, match=ERR_BLOG_REWRITE_EMPTY):
            await self._run(_db(persona=self._persona_model()), "   ")

    async def test_rewrite_output_is_display_sanitized(self) -> None:
        text = await self._run(_db(persona=self._persona_model()), "Olá <b>mundo</b>")
        assert "<" not in text and ">" not in text


def test_blog_image_is_frozen_model() -> None:
    assert BlogImage(url="/x.jpg", alt="a").caption is None
