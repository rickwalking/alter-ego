"""API tests: image slots, section rewrite, EN translation, strict suggest.

Feature: backend/tests/features/blog_post_ai_contract_ae0424.feature
Feature: frontend/tests/features/blog_editor_ae0424.feature (backend half)
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from rag_backend.agents.blog_editor_prompts import (
    image_prompt,
    translate_section_prompt,
)
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
    BLOG_IMAGE_PRUNE_GRACE_SECONDS,
    ERR_BLOG_IMAGE_BUDGET_EXHAUSTED,
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
    put,
    set_fields,
    three_sections,
    versions,
)

PROVIDER_URL = "https://provider.example/tmp/x.png"


@pytest.fixture
async def clients(tmp_path: Path) -> AsyncIterator[EditorClients]:
    async with editor_clients(tmp_path) as built:
        yield built


def _age(path: Path) -> None:
    """Move a file's mtime past the prune grace window."""
    old = time.time() - BLOG_IMAGE_PRUNE_GRACE_SECONDS - 60
    os.utime(path, (old, old))


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"png-body"


class _Provider:
    """Writes PNG bytes (what gpt-image-2 returns); ``during`` runs mid-spend.

    ``after_write`` runs after the bytes are on disk (the image waits for the row lock).
    """

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0
        self.during: Callable[[], Awaitable[None]] | None = None
        self.after_write: Callable[[], Awaitable[None]] | None = None

    async def generate_image(self, prompt: str, output_path: str) -> str:
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        if self.during is not None:
            await self.during()
        Path(output_path).write_bytes(PNG_BYTES)
        if self.after_write is not None:
            await self.after_write()
        return PROVIDER_URL


@pytest.fixture
def provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Provider:
    from rag_backend.api.dependencies import blog_editor
    from rag_backend.api.routes import blog_post_images

    fake = _Provider()
    store = BlogImageStore(root=tmp_path / "store", cdn=AssetCdnService())
    monkeypatch.setattr(
        blog_post_images,
        "build_blog_image_service",
        lambda: BlogImageService(fake, store, image_prompt),
    )
    monkeypatch.setattr(blog_post_images, "blog_images_store", lambda: store)
    monkeypatch.setattr(blog_editor, "blog_images_store", lambda: store)
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
        assert image["url"].endswith(".png")
        served = await clients.author.get(image["url"])
        assert served.status_code == 200
        assert served.content == PNG_BYTES
        assert served.headers["content-type"] == "image/png"
        assert served.headers["cache-control"] == "private, no-store"
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
        generated = (
            await clients.author.post(url, json={}, headers=if_match(post))
        ).json()
        patched = await clients.author.patch(
            url,
            json={"alt": "Gráfico de custos", "caption": "Fonte: OpenAI"},
            headers=if_match(generated),
        )
        assert patched.status_code == 200, patched.text
        image = patched.json()["content"]["sections"][0]["image"]
        assert (image["alt"], image["caption"]) == (
            "Gráfico de custos",
            "Fonte: OpenAI",
        )
        removed = await clients.author.delete(url, headers=if_match(patched.json()))
        assert removed.status_code == 200
        assert removed.json()["content"]["sections"][0]["image"] is None

    # Scenario: An empty alt is rejected
    async def test_blank_alt_patch_is_422(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        post = await create_post(clients.author, three_sections())
        url = _section_image_url(post["id"])
        generated = (
            await clients.author.post(url, json={}, headers=if_match(post))
        ).json()
        response = await clients.author.patch(
            url, json={"alt": "  "}, headers=if_match(generated)
        )
        assert response.status_code == 422

    async def test_patch_without_image_is_404(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, three_sections())
        response = await clients.author.patch(
            _section_image_url(post["id"]),
            json={"caption": "x"},
            headers=if_match(post),
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
            _section_image_url(post["id"], "sec_unknown"),
            json={},
            headers=if_match(post),
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
        assert (cover["alt"], first["featured_image_url"]) == (
            "GPT 5.6 saiu",
            cover["url"],
        )
        second = (
            await clients.author.post(url, json={}, headers=if_match(first))
        ).json()
        assert second["content"]["cover"]["url"] != cover["url"]
        assert second["featured_image_url"] == second["content"]["cover"]["url"]
        patched = await clients.author.patch(
            url, json={"caption": "Capa"}, headers=if_match(second)
        )
        assert patched.json()["content"]["cover"]["caption"] == "Capa"
        removed = (
            await clients.author.delete(url, headers=if_match(patched.json()))
        ).json()
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

    async def test_draft_images_are_author_only_until_published(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        """A non-published post's images 404 for everyone but its author/admin;
        published images are public with a revalidated cache.
        """
        post = await create_post(clients.author, three_sections())
        generated = await clients.author.post(
            _section_image_url(post["id"]), json={}, headers=if_match(post)
        )
        url = generated.json()["content"]["sections"][0]["image"]["url"]
        async with AsyncClient(
            transport=clients.author._transport, base_url="http://test"
        ) as anonymous:
            assert (await anonymous.get(url)).status_code == 404
            assert (await clients.reviewer.get(url)).status_code == 404
            await set_fields(post["id"], status=BlogPostStatus.PUBLISHED.value)
            public = await anonymous.get(url)
        assert public.status_code == 200
        assert (
            public.headers["cache-control"] == "public, max-age=3600, must-revalidate"
        )

    async def test_unknown_post_is_404(self, clients: EditorClients) -> None:
        url = "/api/blog-images/00000000-0000-4000-8000-000000000009/00000000-0000-4000-8000-000000000000.png"
        assert (await clients.author.get(url)).status_code == 404


class TestSlotWriteContract:
    """The paid result survives concurrent writes (editor/generation contract)."""

    async def test_save_during_generation_keeps_both(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        """A Save (or another slot) commits while the provider runs: the slot is applied
        onto the LATEST document, no 409, both changes kept.
        """
        post = await create_post(clients.author, three_sections())
        saved = dict(post["content"])
        saved["sections"] = [dict(x) for x in post["content"]["sections"]]
        saved["sections"][1]["body_md"] = "Salvo durante a geração"

        async def concurrent_save() -> None:
            await set_fields(
                post["id"], content=saved, lock_version=post["lock_version"] + 1
            )

        provider.during = concurrent_save
        response = await clients.author.post(
            _section_image_url(post["id"]), json={}, headers=if_match(post)
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["content"]["sections"][0]["image"] is not None
        assert body["content"]["sections"][1]["body_md"] == "Salvo durante a geração"
        assert body["lock_version"] == post["lock_version"] + 2

    async def test_section_deleted_during_generation_leaves_no_orphan(
        self, clients: EditorClients, provider: _Provider, tmp_path: Path
    ) -> None:
        """The section is deleted during the spend: 404 and the new file is gone."""
        post = await create_post(clients.author, three_sections())
        without_first = dict(post["content"])
        without_first["sections"] = post["content"]["sections"][1:]

        async def delete_section() -> None:
            await set_fields(post["id"], content=without_first)

        provider.during = delete_section
        response = await clients.author.post(
            _section_image_url(post["id"]), json={}, headers=if_match(post)
        )
        assert response.status_code == 404
        assert response.json()["detail"] == ERR_BLOG_SECTION_NOT_FOUND
        folder = tmp_path / "store" / post["id"]
        assert not folder.exists() or not any(folder.iterdir())

    async def test_image_budget_is_enforced_before_spend(
        self,
        clients: EditorClients,
        provider: _Provider,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from rag_backend.api.routes import blog_post_images

        monkeypatch.setattr(blog_post_images, "blog_image_cost_cap", lambda: 1)
        post = await create_post(clients.author, three_sections())
        first = await clients.author.post(
            _section_image_url(post["id"]), json={}, headers=if_match(post)
        )
        assert first.json()["ai_generation_metadata"]["blog_image_generations"] == 1
        second = await clients.author.post(
            _section_image_url(post["id"], SEC_2),
            json={},
            headers=if_match(first.json()),
        )
        assert second.status_code == 429
        assert second.json()["detail"] == ERR_BLOG_IMAGE_BUDGET_EXHAUSTED
        assert provider.calls == 1

    async def test_unreferenced_files_are_pruned(
        self, clients: EditorClients, provider: _Provider, tmp_path: Path
    ) -> None:
        """Regenerate keeps the old file while a version snapshot references it; once
        nothing references it, the next write deletes it. The second image lives on in
        the pre-remove version snapshot (restorable).
        """
        post = await create_post(clients.author, three_sections())
        url = _section_image_url(post["id"])
        first = (await clients.author.post(url, json={}, headers=if_match(post))).json()
        second = (
            await clients.author.post(url, json={}, headers=if_match(first))
        ).json()
        folder = tmp_path / "store" / post["id"]
        assert len(list(folder.iterdir())) == 2
        for path in folder.iterdir():
            _age(path)
        await set_fields(post["id"], version_history=[])
        await clients.author.delete(url, headers=if_match(second))
        kept = second["content"]["sections"][0]["image"]["url"].rsplit("/", 1)[-1]
        assert [p.name for p in folder.iterdir()] == [kept]


class TestPruneRaces:
    """Pruning never breaks an in-flight image."""

    async def test_save_between_generate_and_write_keeps_the_image(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        """A Save lands after the image file is written but before its slot write: the
        Save's prune must not delete the pending file.
        """
        post = await create_post(clients.author, three_sections())
        edited = dict(post["content"])
        edited["sections"] = [dict(x) for x in post["content"]["sections"]]
        edited["sections"][2]["body_md"] = "Salvo no meio"

        async def save_now() -> None:
            response = await put(clients.author, post, {"content": edited})
            assert response.status_code == 200, response.text

        provider.after_write = save_now
        response = await clients.author.post(
            _section_image_url(post["id"]), json={}, headers=if_match(post)
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["content"]["sections"][2]["body_md"] == "Salvo no meio"
        served = await clients.author.get(
            body["content"]["sections"][0]["image"]["url"]
        )
        assert served.status_code == 200

    async def test_cutover_stash_and_featured_image_are_kept(
        self, clients: EditorClients, provider: _Provider, tmp_path: Path
    ) -> None:
        """The cutover rollback stash and the featured_image_url column are references
        too (even when old), so --rollback never restores a dead URL.
        """
        post = await create_post(clients.author, three_sections())
        folder = tmp_path / "store" / post["id"]
        folder.mkdir(parents=True)
        stash = folder / "00000000-0000-4000-8000-00000000000a.png"
        featured = folder / "00000000-0000-4000-8000-00000000000b.png"
        orphan = folder / "00000000-0000-4000-8000-00000000000c.png"
        for path in (stash, featured, orphan):
            path.write_bytes(PNG_BYTES)
            _age(path)
        prefix = f"/api/blog-images/{post['id']}"
        await set_fields(
            post["id"],
            featured_image_url=f"{prefix}/{featured.name}",
            ai_generation_metadata={
                "blog_v2_cutover": {"featured_image_url": f"{prefix}/{stash.name}"}
            },
        )
        response = await put(clients.author, post, {"title": "Novo"})
        assert response.status_code == 200, response.text
        assert stash.exists() and featured.exists()
        assert not orphan.exists()


class TestImageBudgetReservation:
    """The budget is reserved under the row lock before the provider call."""

    async def test_parallel_requests_at_cap_minus_one(
        self,
        clients: EditorClients,
        provider: _Provider,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from rag_backend.api.routes import blog_post_images

        monkeypatch.setattr(blog_post_images, "blog_image_cost_cap", lambda: 1)
        post = await create_post(clients.author, three_sections())
        responses = await asyncio.gather(
            clients.author.post(
                _section_image_url(post["id"], SEC_1), json={}, headers=if_match(post)
            ),
            clients.author.post(
                _section_image_url(post["id"], SEC_2), json={}, headers=if_match(post)
            ),
        )
        codes = sorted(r.status_code for r in responses)
        assert codes == [200, 429]
        assert provider.calls == 1

    async def test_failed_write_keeps_the_reservation(
        self, clients: EditorClients, provider: _Provider
    ) -> None:
        """The reservation is kept when the write fails after the spend."""
        post = await create_post(clients.author, three_sections())
        without_first = dict(post["content"])
        without_first["sections"] = post["content"]["sections"][1:]

        async def delete_section() -> None:
            await set_fields(post["id"], content=without_first)

        provider.during = delete_section
        response = await clients.author.post(
            _section_image_url(post["id"]), json={}, headers=if_match(post)
        )
        assert response.status_code == 404
        stored = await get_post(clients.author, post["id"])
        assert stored["ai_generation_metadata"]["blog_image_generations"] == 1


def _fake_ai(monkeypatch: pytest.MonkeyPatch, result: str | Exception) -> MagicMock:
    from rag_backend.api.routes import blog_post_sections

    fake = MagicMock()
    fake.rewrite_section = AsyncMock(
        side_effect=result if isinstance(result, Exception) else None,
        return_value=result,
    )
    monkeypatch.setattr(blog_post_sections, "_build_ai_service", lambda: fake)
    return fake


class TestRewritePersonaResolution:
    """Scenario: Rewriting a section without a persona uses the default persona."""

    def _target(self, persona_id: str | None) -> MagicMock:
        target = MagicMock()
        project = MagicMock(persona_id=persona_id)
        target.repo.get_project_by_id = AsyncMock(return_value=project)
        return target

    async def test_requested_persona_wins(self) -> None:
        from rag_backend.api.routes.blog_post_sections import _persona_id

        target = self._target("p-project")
        assert (
            await _persona_id(target, "11111111-1111-4111-8111-111111111111", "p1")
            == "p1"
        )
        target.repo.get_project_by_id.assert_not_awaited()

    async def test_project_persona_is_the_default(self) -> None:
        from rag_backend.api.routes.blog_post_sections import _persona_id

        target = self._target("p-project")
        project_id = "11111111-1111-4111-8111-111111111111"
        assert await _persona_id(target, project_id, None) == "p-project"

    async def test_no_project_or_unbound_persona_is_none(self) -> None:
        from rag_backend.api.routes.blog_post_sections import _persona_id

        assert await _persona_id(self._target("x"), None, None) is None
        project_id = "11111111-1111-4111-8111-111111111111"
        assert await _persona_id(self._target(None), project_id, None) is None


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
        before, after = (
            post["content"]["sections"],
            response.json()["content"]["sections"],
        )
        assert after[1]["body_md"] == "Na minha voz"
        assert (after[0], after[2]) == (before[0], before[2])
        sent = fake.rewrite_section.await_args.args[0]
        assert (sent.body_md, sent.heading, sent.persona_id) == (
            "Corpo dois",
            "Dois",
            "p1",
        )

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
        lambda: BlogTranslationService(llm, translate_section_prompt),
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
        service = BlogPostAIService(llm_service=llm)
        monkeypatch.setattr(blog_post_ai, "_build_ai_service", lambda: service)
        post = await create_post(clients.author, three_sections())
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/ai-suggest", json={"text": "texto"}
        )
        assert response.status_code == 200, response.text
        assert response.json()["suggested_text"] == expected
        assert "```" not in json.dumps(response.json())
