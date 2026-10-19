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

from rag_backend.agents.blog_editor_prompts import (
    image_prompt,
    translate_section_prompt,
)
from rag_backend.application.services.asset_cdn_service import AssetCdnService
from rag_backend.application.services.blog.blog_image_service import (
    BlogImageError,
    BlogImageRequest,
    BlogImageService,
    default_scene,
)
from rag_backend.application.services.blog.blog_image_store import (
    BlogImageStore,
    referenced_filenames,
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
    ERR_BLOG_REWRITE_TOO_LONG,
)
from rag_backend.domain.models.blog_document import BlogImage, parse_blog_content
from tests.blog_v2_support import v2_content, v2_section

POST_ID = "11111111-1111-4111-8111-111111111111"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 16
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 16
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"0" * 8
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
    with (
        patch(targets[0], return_value=context),
        patch(targets[1], return_value=context),
        patch(targets[2], return_value=context),
    ):
        yield


class _WritingProvider:
    """Writes bytes to the requested path and returns a provider URL."""

    def __init__(self, payload: bytes = PNG_BYTES) -> None:
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
        image = await BlogImageService(
            provider, _store(tmp_path), image_prompt
        ).generate(_request())
        assert image.url.startswith(f"/api/blog-images/{POST_ID}/")
        # gpt-image-2 returns PNG: the file is named (and served) as .png.
        assert image.url.endswith(".png")
        assert PROVIDER_URL not in image.model_dump_json()
        stored = tmp_path / "blog-images" / POST_ID / image.url.rsplit("/", 1)[1]
        assert stored.read_bytes() == PNG_BYTES
        assert not list((tmp_path / "blog-images" / POST_ID).glob("*.part"))
        assert image.alt == "O que aconteceu"
        assert image.model == "gpt-image-2"
        assert image.source == "generated"
        assert image.prompt == "Um farol na costa"

    async def test_template_forbids_text_and_wraps_the_scene(
        self, tmp_path: Path
    ) -> None:
        provider = _WritingProvider()
        await BlogImageService(provider, _store(tmp_path), image_prompt).generate(
            _request()
        )
        prompt = provider.prompts[0]
        assert "no text, no words, no letters, no numbers" in prompt
        assert "Um farol na costa" in prompt

    async def test_image_prompt_sanitizer_is_applied(self, tmp_path: Path) -> None:
        provider = _WritingProvider()
        image = await BlogImageService(
            provider, _store(tmp_path), image_prompt
        ).generate(_request("Elon Musk on stage"))
        assert "Musk" not in provider.prompts[0]
        assert "Musk" not in (image.prompt or "")

    async def test_cdn_url_when_enabled(self, tmp_path: Path) -> None:
        cdn = AssetCdnService(cdn_base_url="https://cdn.example", enabled=True)
        image = await BlogImageService(
            _WritingProvider(), _store(tmp_path, cdn), image_prompt
        ).generate(_request())
        assert image.url.startswith(f"https://cdn.example/blog-images/{POST_ID}/")

    # Scenario: A failed image generation shows a visible retry (backend: 502 code)
    async def test_provider_failure_raises_generation_failed(
        self, tmp_path: Path
    ) -> None:
        provider = MagicMock()
        provider.generate_image = AsyncMock(side_effect=RuntimeError("boom"))
        with pytest.raises(BlogImageError) as exc:
            await BlogImageService(provider, _store(tmp_path), image_prompt).generate(
                _request()
            )
        assert exc.value.code == ERR_BLOG_IMAGE_GENERATION_FAILED

    async def test_missing_file_is_a_persist_failure(self, tmp_path: Path) -> None:
        with pytest.raises(BlogImageError) as exc:
            await BlogImageService(
                _WritingProvider(b""), _store(tmp_path), image_prompt
            ).generate(_request())
        assert exc.value.code == ERR_BLOG_IMAGE_PERSIST_FAILED

    async def test_no_provider_is_a_generation_failure(self, tmp_path: Path) -> None:
        with pytest.raises(BlogImageError) as exc:
            await BlogImageService(None, _store(tmp_path), image_prompt).generate(
                _request()
            )
        assert exc.value.code == ERR_BLOG_IMAGE_GENERATION_FAILED

    @pytest.mark.parametrize(
        ("payload", "extension"),
        [(PNG_BYTES, ".png"), (JPEG_BYTES, ".jpg"), (WEBP_BYTES, ".webp")],
    )
    async def test_real_type_decides_the_extension(
        self, tmp_path: Path, payload: bytes, extension: str
    ) -> None:
        service = BlogImageService(
            _WritingProvider(payload), _store(tmp_path), image_prompt
        )
        image = await service.generate(_request())
        assert image.url.endswith(extension)

    async def test_unknown_bytes_are_a_persist_failure(self, tmp_path: Path) -> None:
        service = BlogImageService(
            _WritingProvider(b"not an image"), _store(tmp_path), image_prompt
        )
        with pytest.raises(BlogImageError) as exc:
            await service.generate(_request())
        assert exc.value.code == ERR_BLOG_IMAGE_PERSIST_FAILED
        assert not any((tmp_path / "blog-images" / POST_ID).iterdir())

    def test_store_lookup_delete_and_prune(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        path = store.new_path(POST_ID)
        assert store.file_for(POST_ID, path.name) is None
        path.write_bytes(b"x")
        assert store.file_for(POST_ID, path.name) == path
        other = store.new_path(POST_ID)
        other.write_bytes(b"y")
        assert store.prune(POST_ID, {path.name}) == 1
        assert not other.exists()
        store.delete(POST_ID, path.name)
        assert store.file_for(POST_ID, path.name) is None
        assert store.prune("no-such-post", set()) == 0

    def test_referenced_filenames_walks_content_and_history(self) -> None:
        content = {
            "cover": {"url": "/api/blog-images/p/a.png"},
            "sections": [{"image": {"url": "https://cdn/x/b.jpg"}}],
        }
        history = [{"snapshot": {"cover": {"url": "/api/blog-images/p/c.webp"}}}]
        assert referenced_filenames(content, history, None) == {
            "a.png",
            "b.jpg",
            "c.webp",
        }


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


def _translator(answers: list[str]) -> BlogTranslationService:
    return BlogTranslationService(_llm(answers), translate_section_prompt)


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
        service = _translator([f"```json\n{answer}\n```"])
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
        english = await _translator([answer]).translate(POST_ID, document)
        assert english.sections[0].heading is None

    @pytest.mark.parametrize(
        "answer",
        [
            "not json",
            json.dumps({"heading": "x"}),
            json.dumps(["x"]),
            '{"body_md": " "}',
        ],
    )
    async def test_bad_answer_fails_the_translation(self, answer: str) -> None:
        document = parse_blog_content(v2_content("Corpo", "Um"))
        with pytest.raises(BlogTranslationError):
            await _translator([answer]).translate(POST_ID, document)

    async def test_llm_error_fails_the_translation(self) -> None:
        llm = MagicMock()
        llm.generate = AsyncMock(side_effect=TimeoutError())
        document = parse_blog_content(v2_content("Corpo", "Um"))
        with pytest.raises(BlogTranslationError):
            await BlogTranslationService(llm, translate_section_prompt).translate(
                POST_ID, document
            )

    async def test_non_string_heading_becomes_null(self) -> None:
        answer = json.dumps({"heading": 3, "body_md": "Body"})
        document = parse_blog_content(v2_content("Corpo", "Um"))
        english = await _translator([answer]).translate(POST_ID, document)
        assert english.sections[0].heading is None


def _ai_service() -> BlogPostAIService:
    llm = MagicMock()
    llm.chat_model = MagicMock()
    return BlogPostAIService(llm_service=llm)


def _db(persona: object | None = None, project: object | None = None) -> MagicMock:
    db = MagicMock()
    db.get = AsyncMock(
        side_effect=lambda model, _id: (
            project if "Carousel" in model.__name__ else persona
        )
    )
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
    async def test_first_persona_when_nothing_bound(self) -> None:
        db = _db(persona=self._persona_model())
        assert await self._run(db, "Voz") == "Voz"
        db.execute.assert_awaited_once()

    async def test_no_persona_at_all_is_rejected(self) -> None:
        with pytest.raises(ValueError, match=ERR_BLOG_PERSONA_REQUIRED):
            await self._run(_db(persona=None), "Voz")

    async def test_empty_rewrite_is_rejected(self) -> None:
        with pytest.raises(ValueError, match=ERR_BLOG_REWRITE_EMPTY):
            await self._run(_db(persona=self._persona_model()), "   ")

    async def test_rewrite_output_keeps_markdown(self) -> None:
        # The model output is NOT run through the input sanitizer: links and
        # parentheses survive (rendering relies on the markdown allow-list).
        markdown = "Veja [o anúncio](https://example.com) (em inglês) <3"
        text = await self._run(_db(persona=self._persona_model()), markdown)
        assert text == markdown

    async def test_rewrite_longer_than_a_section_is_rejected(self) -> None:
        with pytest.raises(ValueError, match=ERR_BLOG_REWRITE_TOO_LONG):
            await self._run(_db(persona=self._persona_model()), "x" * 20_001)

    async def test_body_longer_than_the_llm_input_is_rejected(self) -> None:
        db = _db(persona=self._persona_model())
        with patch(
            "rag_backend.application.services.blog_post_ai_service.PersonaAgent"
        ) as agent_cls:
            with pytest.raises(ValueError, match=ERR_BLOG_REWRITE_TOO_LONG):
                await _ai_service().rewrite_section(
                    _RewriteInput(db=db, body_md="x" * 10_001)
                )
            agent_cls.assert_not_called()


def test_blog_image_is_frozen_model() -> None:
    assert BlogImage(url="/x.jpg", alt="a").caption is None
