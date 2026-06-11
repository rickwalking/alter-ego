"""Tests for the persistent carousel closing slide."""

import pytest

from rag_backend.application.services.carousel_template.strategies.cta import (
    CtaCenteredStrategy,
)
from rag_backend.domain.protocols.carousel import _RenderOptions


@pytest.mark.unit
class TestCtaCenteredStrategy:
    def test_renders_brand_footer_without_slide_background(
        self,
        sample_project,
        sample_theme,
    ) -> None:
        sample_project.creator_name = "Pedro Marins"
        sample_project.creator_handle = "pedromarins.ai"
        sample_project.creator_avatar_url = "images/about-pedro.jpg"

        result = CtaCenteredStrategy().render(
            {"number": "7", "type": "cta"},
            sample_project,
            sample_theme,
            options=_RenderOptions(total_slides=7, language="pt"),
        )

        assert "Pedro Marins" in result
        assert "@pedromarins.ai" in result
        assert "marinssolutions.com" in result
        assert "Siga para mais conteúdo como esse" in result
        assert "images/about-pedro.jpg" in result
        assert "images/slide_7.jpg" not in result

    def test_uses_staged_creator_asset_when_configured(
        self,
        sample_project,
        sample_theme,
    ) -> None:
        from uuid import uuid4

        staged_path = "assets/creators/abc123.webp"
        sample_project.creator_asset_id = uuid4()
        sample_project.creator_asset_staged_path = staged_path
        sample_project.creator_avatar_url = "images/about-pedro.jpg"

        result = CtaCenteredStrategy().render(
            {"number": "7", "type": "cta"},
            sample_project,
            sample_theme,
            options=_RenderOptions(total_slides=7, language="pt"),
        )

        assert staged_path in result
        assert "images/about-pedro.jpg" not in result
        assert 'class="closing-card"' in result
        assert result.index('class="closing-avatar"') < result.index(
            'class="closing-website"'
        )

    def test_localizes_follow_text_to_english(
        self,
        sample_project,
        sample_theme,
    ) -> None:
        result = CtaCenteredStrategy().render(
            {"number": "7", "type": "cta"},
            sample_project,
            sample_theme,
            options=_RenderOptions(total_slides=7, language="en"),
        )

        assert "Follow for more content like this" in result
