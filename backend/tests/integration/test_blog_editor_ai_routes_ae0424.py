"""API tests: image slots, section rewrite, EN translation, strict suggest (AE-0424).

Feature: backend/tests/features/blog_post_ai_contract_ae0424.feature
Feature: frontend/tests/features/blog_editor_ae0424.feature (backend half)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from rag_backend.application.services.asset_cdn_service import AssetCdnService
from rag_backend.application.services.blog.blog_image_service import (
    BlogImageService,
    BlogImageStore,
)
from rag_backend.application.services.blog.blog_translation_service import (
    BlogTranslationService,
)
from rag_backend.application.services.blog_post_ai_service import BlogPostAIService
from rag_backend.domain.constants.blog_document import ERR_BLOG_DOCUMENT_NOT_V2
from rag_backend.domain.constants.blog_editor import (
    ERR_BLOG_IMAGE_GENERATION_FAILED,
    ERR_BLOG_PERSONA_REQUIRED,
    ERR_BLOG_SECTION_IMAGE_MISSING,
    ERR_BLOG_SECTION_NOT_FOUND,
    ERR_BLOG_TRANSLATION_EXISTS,
    ERR_BLOG_TRANSLATION_MISSING,
)
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.optimistic_locking import (
    ERR_VERSION_CONFLICT,
    HTTP_HEADER_IF_MATCH,
)
from tests.integration.blog_editor_support_ae0424 import (
    BLOG_POSTS_URL,
    SEC_1,
    SEC_2,
    EditorClients,
    create_post,
    editor_clients,
    get_post,
    if_match,
    set_fields,
    three_sections,
    versions,
)

PROVIDER_URL = "https://provider.example/tmp/x.png"


@pytest.fixture
async def clients(tmp_path: Path) -> AsyncIterator[EditorClients]:
    async with editor_clients(tmp_path) as built:
        yield built


class _Provider:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    async def generate_image(self, prompt: str, output_path: str) -> str:
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        Path(output_path).write_bytes(b"jpeg-bytes")
        return PROVIDER_URL


@pytest.fixture
def provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Provider:
    from rag_backend.api.routes import blog_post_images

    fake = _Provider()
    store = BlogImageStore(root=tmp_path / "store", cdn=AssetCdnService())
    monkeypatch.setattr(
        blog_post_images, "build_blog_image_service", lambda: BlogImageService(fake, store)
    )
    monkeypatch.setattr(blog_post_images, "blog_images_store", lambda: store)
    return fake


def _section_image_url(post_id: str, section_id: str = SEC_1) -> str:
    return f"{BLOG_POSTS_URL}/{post_id}/sections/{section_id}/image"


class TestSectionImages:
    # Scenario: Generating a section image stores url, alt and prompt
    async def test_generate_persists_and_serves_the_image(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        post = await create_post(clients.author, three_sections())
        response = await clients.author.post(
            _section_image_url(post["id"]), json={}, headers=if_match(post)
        )
        assert response.status_code == 200, response.text
        image = response.json()["content"]["sections"][0]["image"]
        assert image["url"].startswith(f"/api/blog-images/{post['id']}/")
        assert PROVIDER_URL not in json.dumps(response.json())
        assert (image["alt"], image["model"]) == ("Um", "gpt-image-2")
        assert image["prompt"].startswith("Um. Corpo um")
        served = await clients.author.get(image["url"])
        assert served.status_code == 200
        assert served.content == b"jpeg-bytes"
        async with AsyncClient(
            transport=clients.author._transport, base_url="http://test"
        ) as anonymous:
            assert (await anonymous.get(image["url"])).status_code == 200
        assert len(await versions(clients.author, post["id"])) == 1

    # Scenario: Regenerating uses an edited prompt
    async def test_regenerate_with_edited_prompt(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        post = await create_post(clients.author, three_sections())
        first = (
            await clients.author.post(
                _section_image_url(post["id"]), json={}, headers=if_match(post)
            )
        ).json()
        second = await clients.author.post(
            _section_image_url(post["id"]),
            json={"prompt": "Um farol ao entardecer"},
            headers=if_match(first),
        )
        image = second.json()["content"]["sections"][0]["image"]
        assert image["prompt"] == "Um farol ao entardecer"
        assert image["url"] != first["content"]["sections"][0]["image"]["url"]

    # Scenario: Editing alt and caption persists / Removing clears the slot
    async def test_patch_then_remove(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        post = await create_post(clients.author, three_sections())
        url = _section_image_url(post["id"])
        generated = (await clients.author.post(url, json={}, headers=if_match(post))).json()
        patched = await clients.author.patch(
            url,
            json={"alt": "Gráfico de custos", "caption": "Fonte: OpenAI"},
            headers=if_match(generated),
        )
        assert patched.status_code == 200, patched.text
        image = patched.json()["content"]["sections"][0]["image"]
        assert (image["alt"], image["caption"]) == ("Gráfico de custos", "Fonte: OpenAI")
        removed = await clients.author.delete(url, headers=if_match(patched.json()))
        assert removed.status_code == 200
        assert removed.json()["content"]["sections"][0]["image"] is None

    # Scenario: An empty alt is rejected
    async def test_blank_alt_patch_is_422(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        post = await create_post(clients.author, three_sections())
        url = _section_image_url(post["id"])
        generated = (await clients.author.post(url, json={}, headers=if_match(post))).json()
        response = await clients.author.patch(
            url, json={"alt": "  "}, headers=if_match(generated)
        )
        assert response.status_code == 422

    async def test_patch_without_image_is_404(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, three_sections())
        response = await clients.author.patch(
            _section_image_url(post["id"]), json={"caption": "x"}, headers=if_match(post)
        )
        assert response.status_code == 404
        assert response.json()["detail"] == ERR_BLOG_SECTION_IMAGE_MISSING

    # Scenario: A failed image generation shows a visible retry
    async def test_provider_failure_is_502_and_slot_unchanged(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        provider.fail = True
        post = await create_post(clients.author, three_sections())
        response = await clients.author.post(
            _section_image_url(post["id"]), json={}, headers=if_match(post)
        )
        assert response.status_code == 502
        assert response.json()["detail"] == ERR_BLOG_IMAGE_GENERATION_FAILED
        stored = await get_post(clients.author, post["id"])
        assert stored["content"]["sections"][0]["image"] is None
        assert stored["lock_version"] == post["lock_version"]

    # Scenario: Every content-mutating route enforces If-Match
    async def test_stale_if_match_fails_before_any_spend(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        post = await create_post(clients.author, three_sections())
        stale = {HTTP_HEADER_IF_MATCH: str(post["lock_version"] - 1)}
        response = await clients.author.post(
            _section_image_url(post["id"]), json={}, headers=stale
        )
        assert response.status_code == 409
        assert response.json()["detail"] == ERR_VERSION_CONFLICT
        assert provider.calls == 0
        missing = await clients.author.delete(_section_image_url(post["id"]))
        assert missing.status_code == 428

    async def test_unknown_section_is_404(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        post = await create_post(clients.author, three_sections())
        response = await clients.author.post(
            _section_image_url(post["id"], "sec_unknown"), json={}, headers=if_match(post)
        )
        assert response.status_code == 404
        assert response.json()["detail"] == ERR_BLOG_SECTION_NOT_FOUND
        assert provider.calls == 0

    # Scenario: A non-migrated row shows a blocking migration banner (API half)
    async def test_legacy_row_is_422_before_any_spend(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        post = await create_post(clients.author, three_sections())
        await set_fields(post["id"], content={"markdown": "## A\n\nb"})
        response = await clients.author.post(
            _section_image_url(post["id"]), json={}, headers=if_match(post)
        )
        assert response.status_code == 422
        assert response.json()["detail"] == ERR_BLOG_DOCUMENT_NOT_V2
        assert provider.calls == 0

    async def test_generating_resets_an_approved_post(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        post = await create_post(clients.author, three_sections())
        await set_fields(post["id"], status=BlogPostStatus.APPROVED.value)
        response = await clients.author.post(
            _section_image_url(post["id"]), json={}, headers=if_match(post)
        )
        assert response.json()["status"] == BlogPostStatus.DRAFT.value


class TestCover:
    # Scenario: The cover can be generated, regenerated and removed
    async def test_cover_lifecycle_keeps_featured_image_in_sync(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        post = await create_post(clients.author, three_sections())
        url = f"{BLOG_POSTS_URL}/{post['id']}/cover/image"
        first = (await clients.author.post(url, json={}, headers=if_match(post))).json()
        cover = first["content"]["cover"]
        assert (cover["alt"], first["featured_image_url"]) == ("GPT 5.6 saiu", cover["url"])
        second = (await clients.author.post(url, json={}, headers=if_match(first))).json()
        assert second["content"]["cover"]["url"] != cover["url"]
        assert second["featured_image_url"] == second["content"]["cover"]["url"]
        patched = await clients.author.patch(
            url, json={"caption": "Capa"}, headers=if_match(second)
        )
        assert patched.json()["content"]["cover"]["caption"] == "Capa"
        removed = (await clients.author.delete(url, headers=if_match(patched.json()))).json()
        assert removed["content"]["cover"] is None
        assert removed["featured_image_url"] is None

    async def test_en_cover_needs_a_translation(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        post = await create_post(clients.author, three_sections())
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/cover/image?language=en",
            json={},
            headers=if_match(post),
        )
        assert response.status_code == 404
        assert response.json()["detail"] == ERR_BLOG_TRANSLATION_MISSING


class TestBlogImageServing:
    async def test_bad_or_missing_names_are_404(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        post = await create_post(clients.author, three_sections())
        base = f"/api/blog-images/{post['id']}"
        assert (await clients.author.get(f"{base}/..%2Fsecret.jpg")).status_code == 404
        missing = "00000000-0000-4000-8000-000000000000.jpg"
        assert (await clients.author.get(f"{base}/{missing}")).status_code == 404


def _fake_ai(monkeypatch: pytest.MonkeyPatch, result: str | Exception) -> MagicMock:
    from rag_backend.api.routes import blog_post_sections

    fake = MagicMock()
    fake.rewrite_section = AsyncMock(
        side_effect=result if isinstance(result, Exception) else None,
        return_value=result,
    )
    monkeypatch.setattr(blog_post_sections, "_build_ai_service", lambda: fake)
    return fake


class TestRewriteSection:
    # Scenario: Rewriting a section replaces only that section's body
    async def test_rewrite_replaces_only_that_body(
        self, clients: EditorClients, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _fake_ai(monkeypatch, "Na minha voz")
        post = await create_post(clients.author, three_sections())
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/sections/{SEC_2}/rewrite",
            json={"persona_id": "p1"},
            headers=if_match(post),
        )
        assert response.status_code == 200, response.text
        before, after = post["content"]["sections"], response.json()["content"]["sections"]
        assert after[1]["body_md"] == "Na minha voz"
        assert (after[0], after[2]) == (before[0], before[2])
        sent = fake.rewrite_section.await_args.args[0]
        assert (sent.body_md, sent.heading, sent.persona_id) == ("Corpo dois", "Dois", "p1")

    # Scenario: Rewriting a section without a persona uses the default persona
    async def test_no_persona_anywhere_is_422(
        self, clients: EditorClients, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _fake_ai(monkeypatch, ValueError(ERR_BLOG_PERSONA_REQUIRED))
        post = await create_post(clients.author, three_sections())
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/sections/{SEC_1}/rewrite",
            json={},
            headers=if_match(post),
        )
        assert response.status_code == 422
        assert response.json()["detail"] == ERR_BLOG_PERSONA_REQUIRED

    # Scenario: Rewriting an unknown section returns 404
    async def test_unknown_section_is_404(
        self, clients: EditorClients, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _fake_ai(monkeypatch, "x")
        post = await create_post(clients.author, three_sections())
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/sections/sec_unknown/rewrite",
            json={},
            headers=if_match(post),
        )
        assert response.status_code == 404
        fake.rewrite_section.assert_not_awaited()

    # Scenario: Every content-mutating route enforces If-Match
    async def test_stale_if_match_is_409(
        self, clients: EditorClients, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _fake_ai(monkeypatch, "x")
        post = await create_post(clients.author, three_sections())
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/sections/{SEC_1}/rewrite",
            json={},
            headers={HTTP_HEADER_IF_MATCH: "99"},
        )
        assert response.status_code == 409
        fake.rewrite_section.assert_not_awaited()


def _translator(monkeypatch: pytest.MonkeyPatch, answer: str) -> MagicMock:
    from rag_backend.api.routes import blog_post_sections

    llm = MagicMock()
    llm.generate = AsyncMock(return_value=answer)
    monkeypatch.setattr(
        blog_post_sections,
        "build_blog_translation_service",
        lambda: BlogTranslationService(llm),
    )
    return llm


class TestEnTranslation:
    # Scenario: A missing EN translation is read-only with a generate action
    async def test_generate_then_conflict(
        self, clients: EditorClients, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _translator(monkeypatch, json.dumps({"heading": "One", "body_md": "Body"}))
        post = await create_post(clients.author, three_sections())
        url = f"{BLOG_POSTS_URL}/{post['id']}/translations/en"
        response = await clients.author.post(url, headers=if_match(post))
        assert response.status_code == 200, response.text
        english = response.json()["content"]["translations"]["en"]
        assert [s["body_md"] for s in english["sections"]] == ["Body"] * 3
        assert response.json()["content"]["sections"] == post["content"]["sections"]
        again = await clients.author.post(url, headers=if_match(response.json()))
        assert again.status_code == 409
        assert again.json()["detail"] == ERR_BLOG_TRANSLATION_EXISTS

    async def test_bad_model_answer_is_502(
        self, clients: EditorClients, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _translator(monkeypatch, "not json")
        post = await create_post(clients.author, three_sections())
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/translations/en", headers=if_match(post)
        )
        assert response.status_code == 502
        stored = await get_post(clients.author, post["id"])
        assert stored["content"]["translations"] == {}


class TestStrictSuggest:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ('```json\n{"suggested_text":"Sharper lede"}\n```', "Sharper lede"),
            (json.dumps({"suggested_text": '{"suggested_text":"Inner"}'}), "Inner"),
            ("Just improve it, please", "Just improve it, please"),
            ("", ""),
        ],
    )
    async def test_suggested_text_is_plain(
        self,
        clients: EditorClients,
        monkeypatch: pytest.MonkeyPatch,
        raw: str,
        expected: str,
    ) -> None:
        from rag_backend.api.routes import blog_post_ai

        llm = MagicMock()
        llm.generate = AsyncMock(return_value=raw)
        service = BlogPostAIService(llm_service=llm, image_service=None, output_dir=Path("."))
        monkeypatch.setattr(blog_post_ai, "_build_ai_service", lambda: service)
        post = await create_post(clients.author, three_sections())
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/ai-suggest", json={"text": "texto"}
        )
        assert response.status_code == 200, response.text
        assert response.json()["suggested_text"] == expected
        assert "```" not in json.dumps(response.json())
