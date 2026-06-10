"""Carousel consolidation integration tests.

Feature: carousel_pipeline_consolidation.feature
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from rag_backend.domain.constants.carousel_workflow import (
    ERR_CAROUSEL_NOT_COMPLETED,
    ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.models import CarouselStatus, UserRole
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    create_carousel,
    create_minimal_carousel_artifacts,
    create_user,
    repo_root,
    set_carousel_status,
    set_workflow_status,
)


class TestLegacyEndpointsRemoved:
    """Scenario: Legacy generate endpoint returns 404 or 410."""

    @pytest.mark.asyncio
    async def test_legacy_generate_returns_gone(self, client: AsyncClient) -> None:
        editor = await create_user("editor@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor)
        response = await client.post(
            f"/api/carousels/{project_id}/generate",
            json={"sources": []},
            headers=auth_header(editor),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_legacy_stream_returns_gone(self, client: AsyncClient) -> None:
        editor = await create_user("editor2@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor)
        response = await client.get(
            f"/api/carousels/{project_id}/stream",
            headers=auth_header(editor),
        )
        assert response.status_code == 404


class TestBlogVisibility:
    """Scenarios: draft blog hidden from public routes including admin."""

    @pytest.mark.asyncio
    async def test_anonymous_cannot_read_draft_blog(self, client: AsyncClient) -> None:
        editor = await create_user("anon-test@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        response = await client.get(f"/api/carousels/{project_id}/blog/pt")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_cannot_read_draft_on_public_route(
        self, client: AsyncClient
    ) -> None:
        # Scenario: Admin cannot read draft blog on public media route
        admin = await create_user("admin@example.com", UserRole.ADMIN)
        project_id = await create_carousel(admin, is_public=False)
        response = await client.get(
            f"/api/carousels/{project_id}/blog/pt",
            headers=auth_header(admin),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_public_blog_when_is_public(self, client: AsyncClient) -> None:
        editor = await create_user("public@example.com", UserRole.EDITOR)
        project_id = await create_carousel(
            editor,
            is_public=True,
            blog_markdown="# Public\n\nVisible",
        )
        response = await client.get(f"/api/carousels/{project_id}/blog/pt")
        assert response.status_code == 200


class TestPreviewRoutes:
    """Scenarios: authenticated preview for drafts."""

    @pytest.mark.asyncio
    async def test_editor_previews_draft_blog(self, client: AsyncClient) -> None:
        editor = await create_user("preview@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        response = await client.get(
            f"/api/carousels/{project_id}/preview/blog/pt",
            headers=auth_header(editor),
        )
        assert response.status_code == 200
        payload = response.json()
        assert "markdown" in payload

    @pytest.mark.asyncio
    async def test_anonymous_cannot_access_preview(self, client: AsyncClient) -> None:
        editor = await create_user("preview2@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        response = await client.get(f"/api/carousels/{project_id}/preview/blog/pt")
        assert response.status_code == 401


class TestPreviewAccessControl:
    """Scenario: Non-owner editor cannot preview another user's draft."""

    @pytest.mark.asyncio
    async def test_non_owner_editor_cannot_preview_draft(
        self, client: AsyncClient
    ) -> None:
        owner = await create_user("owner@example.com", UserRole.EDITOR)
        other = await create_user("other-editor@example.com", UserRole.EDITOR)
        project_id = await create_carousel(owner, is_public=False)
        response = await client.get(
            f"/api/carousels/{project_id}/preview/blog/pt",
            headers=auth_header(other),
        )
        assert response.status_code == 403


class TestImageFilenameSanitization:
    """Scenario: Path traversal in image filename is rejected."""

    @pytest.mark.asyncio
    async def test_path_traversal_in_public_image_rejected(
        self, client: AsyncClient
    ) -> None:
        editor = await create_user("path@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=True)
        response = await client.get(
            f"/api/carousels/{project_id}/images/../../../etc/passwd"
        )
        assert response.status_code == 404


class TestPublishSeparation:
    """Scenarios: explicit publish sets is_public; drafts stay hidden."""

    @pytest.mark.asyncio
    async def test_explicit_publish_sets_is_public(self, client: AsyncClient) -> None:
        """Scenario: Explicit publish sets is_public."""
        editor = await create_user("publish@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await create_minimal_carousel_artifacts(project_id)
        await set_workflow_status(project_id, WORKFLOW_STATUS_APPROVED_FOR_PUBLISH)
        await set_carousel_status(project_id, CarouselStatus.COMPLETED)
        response = await client.post(
            f"/api/carousels/{project_id}/publish",
            headers=auth_header(editor),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["is_public"] is True

        public_response = await client.get(f"/api/carousels/{project_id}/blog/pt")
        assert public_response.status_code == 200

    @pytest.mark.asyncio
    async def test_publish_rejected_without_workflow_approval(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Publish blocked when workflow is not approved_for_publish."""
        editor = await create_user("blocked-publish@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        response = await client.post(
            f"/api/carousels/{project_id}/publish",
            headers=auth_header(editor),
        )
        assert response.status_code == 403
        assert response.json()["detail"] == ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH

    @pytest.mark.asyncio
    async def test_publish_rejected_when_carousel_not_completed(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Homepage publish blocked when carousel pipeline is not completed."""
        editor = await create_user("incomplete-publish@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await set_workflow_status(project_id, WORKFLOW_STATUS_APPROVED_FOR_PUBLISH)
        response = await client.post(
            f"/api/carousels/{project_id}/publish",
            headers=auth_header(editor),
        )
        assert response.status_code == 409
        assert response.json()["detail"] == ERR_CAROUSEL_NOT_COMPLETED


class TestCarouselSkillsMigration:
    """Scenario: Shared standards files exist after migration (CP-001)."""

    def test_shared_standards_files_exist(self) -> None:
        root = repo_root()
        shared = root / "skills" / "carousel-pipeline" / "_shared"
        phases = root / "skills" / "carousel-pipeline" / "phases"
        assert (shared / "content-contracts.md").is_file()
        assert (shared / "anti-patterns.md").is_file()
        assert (phases / "content" / "SKILL.md").is_file()

    def test_content_contracts_mentions_slide_types(self) -> None:
        text = (
            repo_root()
            / "skills"
            / "carousel-pipeline"
            / "_shared"
            / "content-contracts.md"
        ).read_text(encoding="utf-8")
        lowered = text.lower()
        assert "intro" in lowered
        assert "closing" in lowered
        assert "cta" in lowered

    def test_shared_standards_preserve_design_and_image_rules(self) -> None:
        """Scenario: Monolithic workflow content is preserved in shared standards."""
        root = repo_root()
        design_text = (
            root / "skills" / "carousel-pipeline" / "_shared" / "design-system.md"
        ).read_text(encoding="utf-8")
        image_text = (
            root / "skills" / "carousel-pipeline" / "_shared" / "image-generation.md"
        ).read_text(encoding="utf-8")
        assert "1080" in design_text
        assert "1350" in design_text
        assert "scene" in image_text.lower()
