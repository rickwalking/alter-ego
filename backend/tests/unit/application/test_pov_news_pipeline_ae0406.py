"""The ``pov_news`` pipeline: brief, prompts, quote cards, render, caption (AE-0406).

Gherkin: tests/features/autopilot_pov_news_ae0406.feature
"""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest

from rag_backend.agents import pov_outline_mixin
from rag_backend.agents.content_draft_agent import (
    ContentDraftAgent,
    _render_content_prompt,
)
from rag_backend.agents.outline_agent import OutlineAgent
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.api.schemas.carousel_content_mode import ContentModeRequestFields
from rag_backend.application.services.carousel.content_mode_brief import (
    brief_for_project,
)
from rag_backend.application.services.carousel.editorial_distribution_pack import (
    _with_news_cards,
    _with_news_footer,
)
from rag_backend.application.services.carousel.editorial_workflow_generators import (
    _with_quote_cards,
)
from rag_backend.application.services.carousel.project_policy import (
    create_time_policy_version,
)
from rag_backend.application.services.carousel.slide_policy_context import (
    slide_policy_context,
)
from rag_backend.application.services.carousel.types import SlideDict
from rag_backend.application.services.carousel_template.builder import (
    CarouselTemplateBuilder,
)
from rag_backend.application.services.carousel_template.prompts import (
    build_caption_prompt,
)
from rag_backend.application.services.carousel_template.role_layouts import (
    pov_slide_strategies,
    quote_card_strategy,
)
from rag_backend.application.services.carousel_template.strategies.insight_quote import (
    InsightQuoteStrategy,
)
from rag_backend.application.services.carousel_template.strategies.registry import (
    bootstrap_strategies,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.pov_prompts import PovHookRequest, PovThesis
from rag_backend.domain.news_quote_cards import quote_card
from rag_backend.domain.protocols.carousel import _RenderOptions
from rag_backend.infrastructure.external.playwright_export_pov import pov_export_css
from tests.unit.autopilot.news_quote_support import THESIS, quote

_Q1 = quote()
_THEME = {"primary": "#3b82f6", "accent": "#f59e0b", "background": "#0a0e17"}
_SOURCES = (
    "https://x.com/kanishksj01/status/1",
    "https://www.anthropic.com/news/x",
    "https://x.com/kanishksj01/status/2",
)


def _project(**changes: object) -> CarouselProject:
    project = CarouselProject(topic="Agentes", audience="Devs", niche="IA")
    project.content_mode = "pov_news"
    project.presentation_policy_version = "pov_hook_v1"
    project.pov_thesis = THESIS
    project.pov_format = "opiniao"
    project.slide_count = 9
    project.cta_goal = "send"
    project.creator_handle = "pedromarins.ai"
    project.pov_quotes = (_Q1,)
    project.pov_sources = _SOURCES
    for key, value in changes.items():
        setattr(project, key, value)
    return project


class TestBrief:
    # Scenario: The carousel is a POV deck with the news voice
    def test_pov_news_is_a_pov_brief_with_the_news_prompts(self) -> None:
        brief = brief_for_project(_project())
        assert brief.is_pov is True
        assert brief.prompt_domain == "carousel_pov_news"
        assert brief.quotes == (_Q1,)
        assert brief.policy.version == "pov_hook_v1"

    def test_pov_keeps_its_prompts(self) -> None:
        brief = brief_for_project(_project(content_mode="pov", pov_quotes=()))
        assert brief.prompt_domain == "carousel_pov"

    def test_create_time_contract(self) -> None:
        assert create_time_policy_version("pov_news") == "pov_hook_v1"
        assert create_time_policy_version("pov") == "pov_hook_v1"
        assert create_time_policy_version(None) == "hero_lower_third_v4"

    def test_slide_context_carries_domain_and_quotes(self) -> None:
        context = slide_policy_context(
            brief_for_project(_project()), {"slide_index": 4, "title": "x"}
        )
        assert context is not None and context.pov is not None
        assert context.pov.role == "point"
        assert context.pov.pov.prompt_domain == "carousel_pov_news"
        assert context.pov.pov.quotes == (_Q1,)


class TestPrompts:
    def test_content_prompt_lists_quotes_on_point_slides(self) -> None:
        context = slide_policy_context(
            brief_for_project(_project()), {"slide_index": 4, "title": "x"}
        )
        text, _ = _render_content_prompt({"slide_number": 4}, context)
        assert "Ponto de Vista: Notícia" in text
        assert "id q1: Kanishk Jain (@kanishksj01)" in text
        assert '"quote_id"' in text
        assert "Telegram" not in text

    def test_content_prompt_hides_quotes_on_other_roles(self) -> None:
        context = slide_policy_context(
            brief_for_project(_project()), {"slide_index": 2, "title": "x"}
        )
        text, _ = _render_content_prompt({"slide_number": 2}, context)
        assert "Kanishk Jain" not in text
        assert "rehook" in text

    def test_pov_content_prompt_is_unchanged(self) -> None:
        context = slide_policy_context(
            brief_for_project(_project(content_mode="pov")), {"slide_index": 4}
        )
        text, _ = _render_content_prompt({"slide_number": 4}, context)
        assert '"Ponto de Vista", seguindo' in text
        assert "quote_id" not in text

    @pytest.mark.parametrize("name", ["outline", "hook", "content", "caption"])
    def test_every_news_prompt_renders(self, name: str) -> None:
        text, config = render_prompt(
            "carousel_pov_news",
            name,
            variables={
                "thesis": THESIS,
                "quotes": [{"id": "q1", "name": "N", "handle": "h", "text_pt": "T"}],
                "roles": ["hook", "point"],
                "slide_count": 9,
                "role": "point",
                "slide_headings": [(1, "Gancho")],
            },
            version="v1",
        )
        assert THESIS in text
        assert "Telegram" not in text
        assert isinstance(config, dict)

    # Scenario: The caption footer is written by code
    def test_caption_uses_the_news_prompt(self) -> None:
        prompt = build_caption_prompt(_project(), [(1, "Gancho"), (2, "Fato")])
        assert "Ponto de Vista: Notícia" in prompt
        assert "o sistema" in prompt
        pov = build_caption_prompt(_project(content_mode="pov"), [(1, "Gancho")])
        assert "Notícia" not in pov

    def test_draft_keeps_the_quote_id(self) -> None:
        agent = ContentDraftAgent.__new__(ContentDraftAgent)
        draft = agent._parse_draft('{"draft_text": "x", "quote_id": " q1 "}')
        assert draft["quote_id"] == "q1"
        assert "quote_id" not in agent._parse_draft(
            '{"draft_text": "x", "quote_id": ""}'
        )

    @pytest.mark.asyncio
    async def test_outline_and_hook_use_the_news_domain(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[str] = []

        def _capture(
            domain: str, name: str, **_: object
        ) -> tuple[str, dict[str, object]]:
            seen.append(f"{domain}/{name}")
            raise RuntimeError("stop")

        monkeypatch.setattr(pov_outline_mixin, "render_prompt", _capture)
        agent = OutlineAgent.__new__(OutlineAgent)
        pov = PovThesis(thesis=THESIS, prompt_domain="carousel_pov_news", quotes=(_Q1,))
        with pytest.raises(RuntimeError):
            await agent.hook_candidates(
                PovHookRequest(topic="t", audience="a", pov=pov)
            )
        assert seen == ["carousel_pov_news/hook"]


class TestQuoteCards:
    # Scenario: A quote is placed verbatim by id, at most twice
    def test_generators_place_cards_only_for_pov_news(self) -> None:
        drafts: list[dict[str, object]] = [
            {"slide_index": 4, "role": "point", "quote_id": "q1"}
        ]
        news = _with_quote_cards(drafts, brief_for_project(_project()))
        assert news[0]["insight"] == quote_card(_Q1, _Q1.text_pt)
        pov = _with_quote_cards(drafts, brief_for_project(_project(content_mode="pov")))
        assert pov is drafts
        assert _with_quote_cards(drafts, None) is drafts

    def test_distribution_adds_en_cards_for_pov_news(self) -> None:
        drafts: list[dict[str, object]] = [
            {"slide_index": 4, "insight": quote_card(_Q1, _Q1.text_pt)}
        ]
        translations: dict[int, dict[str, object]] = {4: {"heading": "H"}}
        cards = _with_news_cards(_project(), translations, drafts)
        assert cards[4]["insight"] == quote_card(_Q1, _Q1.text_en)
        pov = _with_news_cards(_project(content_mode="pov"), translations, drafts)
        assert pov is translations
        empty = _with_news_cards(_project(pov_quotes=()), translations, drafts)
        assert empty is translations

    # Scenario: The caption footer is written by code
    def test_footer_only_on_pov_news(self) -> None:
        assert _with_news_footer(_project(), "Legenda.") == (
            "Legenda.\n\nFontes: @kanishksj01, anthropic.com"
        )
        # Scenario: Radar IA and POV captions get no footer
        assert _with_news_footer(_project(content_mode="pov"), "Legenda.") == "Legenda."


class TestRender:
    def _slide(self, insight: dict[str, str] | None) -> dict[str, object]:
        slide: dict[str, object] = {
            "number": "4",
            "type": "content",
            "heading": "Agentes em paralelo",
            "body": "O custo vai para a revisão.",
        }
        if insight is not None:
            slide["insight"] = insight
        return slide

    def test_quote_slides_use_insight_quote_on_pov_news_only(self) -> None:
        slide = self._slide(quote_card(_Q1, _Q1.text_pt))
        assert quote_card_strategy(_project(), slide) == "insight_quote"
        assert quote_card_strategy(_project(content_mode="pov"), slide) is None
        assert quote_card_strategy(_project(), self._slide(None)) is None
        assert pov_slide_strategies(_project(), 9)[7] == "statement"

    # Scenario: The quote card shows the initial, the name and the handle
    def test_news_card_renders_attribution_without_url(self) -> None:
        card = quote_card(_Q1, "Rodei <b>centenas</b> de agentes.")
        html = InsightQuoteStrategy().render(
            self._slide(card),
            _project(),
            _THEME,
            options=_RenderOptions(total_slides=9, language="pt"),
        )
        assert 'class="quote-avatar" aria-hidden="true">K<' in html
        assert "Kanishk Jain" in html
        assert "@kanishksj01 · X" in html
        assert "&lt;b&gt;centenas&lt;/b&gt;" in html
        assert "https://" not in html
        assert 'data-layout="pov-quote"' in html

    def test_plain_insight_keeps_the_lower_third(self) -> None:
        html = InsightQuoteStrategy().render(
            self._slide({"quote": "Algo", "attribution": "Fonte"}),
            _project(content_mode=None),
            _THEME,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert "— Fonte" in html
        assert "quote-avatar" not in html

    def test_rendered_deck_shows_the_card_on_the_twist(self) -> None:
        kinds = ["intro", *(["content"] * 6), "summary", "cta"]
        slides: list[dict[str, object]] = [
            {"number": str(i), "type": t, "heading": f"Slide {i}", "body": "Corpo"}
            for i, t in enumerate(kinds, 1)
        ]
        slides[6]["insight"] = quote_card(_Q1, _Q1.text_pt)
        html = CarouselTemplateBuilder.build_carousel_html(
            _project(hook_asset_id=uuid4(), hook_asset_staged_path="a/p.webp"),
            cast("list[SlideDict]", slides),
            _THEME,
            strategy_registry=bootstrap_strategies(),
        )
        assert html.count('class="quote-attribution"') == 1
        assert _Q1.text_pt in html

    def test_export_scales_the_card(self) -> None:
        css = pov_export_css(hd=False)
        assert ".quote-avatar" in css and "60px" in css
        assert "120px" in pov_export_css(hd=True)


class TestCreateApi:
    def test_pov_news_follows_pov_rules(self) -> None:
        fields = ContentModeRequestFields(
            content_mode="pov_news",
            pov_thesis=THESIS,
            pov_format="comparacao",
            hook_asset_id=uuid4(),
        )
        fields.check_content_mode()
        assert fields.resolved_pov_format() == "opiniao"
        assert fields.resolved_slide_count() == 9

    def test_pov_news_needs_a_thesis(self) -> None:
        fields = ContentModeRequestFields(
            content_mode="pov_news", hook_asset_id=uuid4()
        )
        with pytest.raises(ValueError, match="pov_thesis is required"):
            fields.check_content_mode()

    def test_pov_news_slide_range(self) -> None:
        fields = ContentModeRequestFields(
            content_mode="pov_news",
            pov_thesis=THESIS,
            hook_asset_id=uuid4(),
            slide_count=7,
        )
        with pytest.raises(ValueError, match="between 8 and 10"):
            fields.check_content_mode()
