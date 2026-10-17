"""Slide 1 with the owner-chosen GrokBot cover (AE-0418, ADR-0024).

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
  Scenario: An ai_image cover renders full-bleed under the title
  Scenario: A screenshot cover renders as a framed card with a credit
  Scenario: A missing cover file fails the render loudly
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel_template.builder import (
    CarouselTemplateBuilder,
)
from rag_backend.application.services.carousel_template.css.slide_styles import (
    _get_neon_slide_css,
)
from rag_backend.application.services.carousel_template.strategies.cover_card import (
    CoverCardStrategy,
    cover_card_strategy,
)
from rag_backend.application.services.carousel_template.strategies.hook_face import (
    HookFaceStrategy,
    HookPhotoError,
)
from rag_backend.application.services.carousel_template.strategies.intro import (
    IntroHeroStrategy,
)
from rag_backend.application.services.carousel_template.strategies.photo_errors import (
    ai_cover_src,
    slide_cover_src,
)
from rag_backend.application.services.carousel_template.strategies.registry import (
    bootstrap_strategies,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.domain.protocols.carousel import _RenderOptions

_THEME = {"primary": "#3b82f6", "accent": "#f59e0b", "background": "#0a0e17"}
_PHOTO = "assets/creators/owner.webp"
_COVER = "assets/creators/grok.webp"
_SLIDE = {"number": "1", "heading": "Agentes em **produção**", "body": "Sub"}


def _cover(kind: str = "ai_image", credit: str = "") -> SlideCover:
    return SlideCover(asset_id=uuid4(), kind=kind, staged_path=_COVER, credit=credit)


def _project(*, pov: bool, cover: SlideCover | None) -> CarouselProject:
    project = CarouselProject(topic="T", audience="Devs", niche="IA")
    if pov:
        project.content_mode = "pov"
        project.presentation_policy_version = "pov_hook_v1"
        project.slide_count = 9
        project.hook_asset_id = uuid4()
        project.hook_asset_staged_path = _PHOTO
    project.creator_handle = "pedromarins.ai"
    project.slide_cover = cover
    return project


def _opts() -> _RenderOptions:
    return _RenderOptions(total_slides=9, language="pt")


@pytest.mark.unit
class TestAiImageCover:
    def test_pov_hook_uses_the_cover_instead_of_the_photo(self) -> None:
        html = HookFaceStrategy().render(
            _SLIDE, _project(pov=True, cover=_cover()), _THEME, options=_opts()
        )
        assert f'src="{_COVER}"' in html
        assert _PHOTO not in html
        assert "pov-hook-photo" in html

    def test_pov_hook_keeps_the_photo_by_default(self) -> None:
        html = HookFaceStrategy().render(
            _SLIDE, _project(pov=True, cover=None), _THEME, options=_opts()
        )
        assert f'src="{_PHOTO}"' in html

    def test_pov_hook_with_a_screenshot_cover_keeps_the_photo(self) -> None:
        project = _project(pov=True, cover=_cover("screenshot"))
        html = HookFaceStrategy().render(_SLIDE, project, _THEME, options=_opts())
        assert f'src="{_PHOTO}"' in html

    def test_radar_intro_uses_the_cover_as_artwork(self) -> None:
        html = IntroHeroStrategy().render(
            _SLIDE, _project(pov=False, cover=_cover()), _THEME, options=_opts()
        )
        assert f'src="{_COVER}"' in html
        assert "images/slide_1.jpg" not in html
        assert "s1-title" in html

    def test_radar_intro_keeps_the_hero_by_default(self) -> None:
        html = IntroHeroStrategy().render(
            _SLIDE, _project(pov=False, cover=None), _THEME, options=_opts()
        )
        assert 'src="images/slide_1.jpg"' in html


@pytest.mark.unit
class TestScreenshotCover:
    @pytest.mark.parametrize("pov", [True, False])
    def test_framed_card_with_title_and_credit(self, *, pov: bool) -> None:
        project = _project(pov=pov, cover=_cover("screenshot", "@poteto · X"))
        html = CoverCardStrategy().render(_SLIDE, project, _THEME, options=_opts())
        assert 'class="cover-card-heading"' in html
        assert "<strong>produção</strong>" in html
        assert f'<img src="{_COVER}"' in html
        assert '<figcaption class="cover-card-credit">@poteto · X</figcaption>' in html
        assert 'data-layout="cover-card"' in html
        assert "Deslize" in html
        assert "images/slide_1.jpg" not in html

    def test_card_without_credit_has_no_caption(self) -> None:
        project = _project(pov=False, cover=_cover("screenshot"))
        html = CoverCardStrategy().render(_SLIDE, project, _THEME, options=None)
        assert "cover-card-credit" not in html

    def test_picked_by_name_without_a_screenshot_is_the_default_intro(self) -> None:
        for cover in (None, _cover()):
            html = CoverCardStrategy().render(
                _SLIDE, _project(pov=False, cover=cover), _THEME, options=_opts()
            )
            assert "s1-title" in html
            assert "cover-card" not in html

    def test_strategy_is_chosen_for_slide_one_only(self) -> None:
        shot = _project(pov=False, cover=_cover("screenshot"))
        assert cover_card_strategy(shot, {"number": "1"}) == "cover_card"
        assert cover_card_strategy(shot, {"number": "2"}) is None
        assert (
            cover_card_strategy(_project(pov=False, cover=_cover()), {"number": "1"})
            is None
        )
        assert (
            cover_card_strategy(_project(pov=False, cover=None), {"number": "1"})
            is None
        )

    def test_css_is_part_of_the_deck(self) -> None:
        css = _get_neon_slide_css(_THEME)
        assert ".cover-card-frame img" in css
        assert "border-radius" in css


@pytest.mark.unit
class TestDeck:
    @pytest.mark.parametrize("pov", [True, False])
    def test_screenshot_deck_renders_the_card_on_slide_one(self, *, pov: bool) -> None:
        slides = [
            {"number": "1", "type": "intro", "heading": "Hook", "body": "Sub"},
            {"number": "2", "type": "content", "heading": "Two", "body": "Body"},
        ]
        project = _project(pov=pov, cover=_cover("screenshot", "theverge.com"))
        html = CarouselTemplateBuilder.build_carousel_html(
            project, slides, _THEME, strategy_registry=bootstrap_strategies()
        )
        assert html.count('data-layout="cover-card"') == 1
        assert "theverge.com" in html


@pytest.mark.unit
class TestStagedFile:
    def test_missing_file_raises(self, tmp_path: Path) -> None:
        project = _project(pov=False, cover=_cover())
        project.output_dir = str(tmp_path)
        with pytest.raises(HookPhotoError) as raised:
            IntroHeroStrategy().render(_SLIDE, project, _THEME, options=_opts())
        assert raised.value.code == "slide_cover_unreadable"
        assert raised.value.project_id == str(project.id)

    def test_staged_file_renders(self, tmp_path: Path) -> None:
        staged = tmp_path / _COVER
        staged.parent.mkdir(parents=True)
        staged.write_bytes(b"webp")
        project = _project(pov=False, cover=_cover("screenshot"))
        project.output_dir = str(tmp_path)
        assert slide_cover_src(project) == _COVER
        assert ai_cover_src(project) is None

    def test_no_cover_has_no_source(self) -> None:
        project = _project(pov=False, cover=None)
        assert slide_cover_src(project) is None
        assert ai_cover_src(project) is None
