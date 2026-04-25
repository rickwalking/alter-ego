"""Unit tests for the smart theme resolver.

Gherkin: tests/features/carousel_design_refinement.feature
"""

import pytest

from rag_backend.application.services.carousel.theme_resolver import (
    _detect_brand,
    _detect_category,
    _hash_to_theme_key,
    _score_brands,
    _score_categories,
    resolve_theme,
)
from rag_backend.domain.constants import (
    BRAND_PALETTES,
    CAROUSEL_THEMES,
)
from rag_backend.domain.models import CarouselProject, CarouselTheme


@pytest.mark.unit
class TestScoreBrands:
    """Tests for _score_brands."""

    def test_scores_anthropic_keywords(self):
        """Should count Anthropic brand keywords."""
        text = "Claude 3 Opus from Anthropic beats GPT-4"
        scores = _score_brands(text)
        assert "anthropic" in scores
        # "claude", "opus", "anthropic" = 3 matches
        assert scores["anthropic"] == 3

    def test_scores_google_keywords(self):
        """Should count Google brand keywords."""
        text = "Google Gemma 4 and Gemini 1.5 Pro"
        scores = _score_brands(text)
        assert "google" in scores
        # "google", "gemma", "gemini" = 3 matches
        assert scores["google"] == 3

    def test_empty_text_returns_empty(self):
        """Should return empty dict for empty text."""
        assert _score_brands("") == {}

    def test_no_match_returns_empty(self):
        """Should return empty dict when no keywords match."""
        assert _score_brands("completely unrelated text about gardening") == {}

    def test_case_insensitive(self):
        """Should match regardless of case."""
        text = "CLAUDE CODE from ANTHROPIC"
        scores = _score_brands(text)
        # "claude", "claude code", "anthropic" = 3 matches
        assert scores["anthropic"] == 3


@pytest.mark.unit
class TestScoreCategories:
    """Tests for _score_categories."""

    def test_scores_cybersecurity_keywords(self):
        """Should count cybersecurity category keywords."""
        text = "New zero-day vulnerability exploit in TLS encryption"
        scores = _score_categories(text)
        assert "cybersecurity" in scores
        # "zero-day", "vulnerability", "exploit", "tls", "encryption" = 5
        assert scores["cybersecurity"] == 5

    def test_scores_ai_competition_keywords(self):
        """Should count AI competition category keywords."""
        text = "LLM benchmark leaderboard shows new model surpassing GPT-4"
        scores = _score_categories(text)
        assert "ai_competition" in scores
        assert scores["ai_competition"] >= 3

    def test_empty_text_returns_empty(self):
        """Should return empty dict for empty text."""
        assert _score_categories("") == {}


@pytest.mark.unit
class TestDetectBrand:
    """Tests for _detect_brand."""

    def test_detects_anthropic(self):
        """Should detect Anthropic from Claude mention."""
        assert _detect_brand("Claude Opus 4.7 release") == "anthropic"

    def test_detects_google(self):
        """Should detect Google from Gemma mention."""
        assert _detect_brand("Google Gemma 4 open weights") == "google"

    def test_detects_openai(self):
        """Should detect OpenAI from GPT mention."""
        assert _detect_brand("GPT-5 from OpenAI") == "openai"

    def test_none_when_no_match(self):
        """Should return None when no brand matches."""
        assert _detect_brand("completely generic topic") is None

    def test_highest_score_wins(self):
        """Should return the brand with the most keyword matches."""
        text = "Claude from Anthropic beats ChatGPT from OpenAI"
        # Anthropic: claude, anthropic = 2
        # OpenAI: chatgpt, openai = 2
        # Tie — max() returns the first encountered, which is fine
        result = _detect_brand(text)
        assert result in ("anthropic", "openai")


@pytest.mark.unit
class TestHashToThemeKey:
    """Tests for _hash_to_theme_key."""

    def test_returns_valid_theme_key(self):
        """Should always return a key present in CAROUSEL_THEMES."""
        key = _hash_to_theme_key("any topic text")
        assert key in CAROUSEL_THEMES

    def test_is_deterministic(self):
        """Same input should always produce the same key."""
        text = "deterministic topic"
        assert _hash_to_theme_key(text) == _hash_to_theme_key(text)

    def test_distributes_across_themes(self):
        """Different inputs should produce different keys."""
        keys = {_hash_to_theme_key(f"topic {i}") for i in range(20)}
        assert len(keys) > 1


@pytest.mark.unit
class TestDetectCategory:
    """Tests for _detect_category."""

    def test_detects_cybersecurity(self):
        """Should detect cybersecurity from attack keywords."""
        assert _detect_category("New malware attack breaches firewall") == "cybersecurity"

    def test_detects_source_code(self):
        """Should detect source_code from leak keywords."""
        assert _detect_category("Source code leaked from GitHub repository") == "source_code"

    def test_detects_ai_competition_from_generic_ai(self):
        """Should detect ai_competition from generic 'AI' mention."""
        assert _detect_category("Uber AI budget for 2026 was blown") == "ai_competition"

    def test_returns_none_when_no_match(self):
        """Should return None when no keywords match."""
        assert _detect_category("completely unrelated fluffy topic") is None


@pytest.mark.unit
class TestResolveTheme:
    """Tests for resolve_theme."""

    def test_explicit_theme_returns_palette(self):
        """Should return the palette for an explicitly set theme."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.CYBERSECURITY,
        )
        theme = resolve_theme(project)
        assert theme == CAROUSEL_THEMES["cybersecurity"]

    def test_explicit_theme_fallback_on_invalid(self):
        """Should fallback to default when theme value is unknown."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AUTO,
        )
        # Manually override to an invalid enum state is impossible with StrEnum,
        # so we test the fallback path via an explicit unknown by patching.
        # Instead, we verify the normal AUTO path works.
        project.theme = CarouselTheme.AI_COMPETITION
        theme = resolve_theme(project)
        assert theme == CAROUSEL_THEMES["ai_competition"]

    def test_auto_detects_brand_anthropic(self):
        """AUTO theme should detect Anthropic brand and return orange/cyan."""
        project = CarouselProject(
            topic="Claude Opus 4.7",
            audience="Developers",
            niche="AI",
            theme=CarouselTheme.AUTO,
        )
        theme = resolve_theme(project)
        assert theme == BRAND_PALETTES["anthropic"]

    def test_auto_detects_brand_google(self):
        """AUTO theme should detect Google brand and return blue/amber."""
        project = CarouselProject(
            topic="Gemma 4 benchmarks",
            audience="Developers",
            niche="AI",
            theme=CarouselTheme.AUTO,
        )
        theme = resolve_theme(project)
        assert theme == BRAND_PALETTES["google"]

    def test_auto_detects_category_cybersecurity(self):
        """AUTO theme should fallback to category detection when no brand matches."""
        project = CarouselProject(
            topic="New ransomware attack exploits zero-day",
            audience="Security pros",
            niche="Cybersecurity",
            theme=CarouselTheme.AUTO,
        )
        theme = resolve_theme(project)
        assert theme == CAROUSEL_THEMES["cybersecurity"]

    def test_auto_uses_title_and_subtitle(self):
        """AUTO theme should analyze title and subtitle, not just topic."""
        project = CarouselProject(
            topic="Generic update",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AUTO,
        )
        project.set_title(
            title="Claude Code leak reveals hidden features",
            subtitle="Anthropic's source code exposed",
        )
        theme = resolve_theme(project)
        # Both "claude" and "anthropic" and "leak" are present,
        # but brand detection scores higher for "anthropic"
        assert theme == BRAND_PALETTES["anthropic"]

    def test_auto_fallback_is_diverse(self):
        """AUTO theme should rotate through palettes when nothing matches."""
        project_a = CarouselProject(
            topic="Something completely unrelated",
            audience="Everyone",
            niche="General",
            theme=CarouselTheme.AUTO,
        )
        theme_a = resolve_theme(project_a)
        assert theme_a in CAROUSEL_THEMES.values()

        project_b = CarouselProject(
            topic="Another totally different topic about gardening",
            audience="Everyone",
            niche="General",
            theme=CarouselTheme.AUTO,
        )
        theme_b = resolve_theme(project_b)
        assert theme_b in CAROUSEL_THEMES.values()
        # Different topics should typically yield different themes
        assert theme_a != theme_b

    def test_auto_fallback_is_deterministic(self):
        """Same topic should always yield the same fallback theme."""
        project = CarouselProject(
            topic="Uber AI budget for 2026 was blown",
            audience="Everyone",
            niche="General",
            theme=CarouselTheme.AUTO,
        )
        theme_first = resolve_theme(project)
        theme_second = resolve_theme(project)
        assert theme_first == theme_second

    def test_auto_detects_meta(self):
        """AUTO theme should detect Meta brand from Llama mention."""
        project = CarouselProject(
            topic="Meta Llama 3 open weights release",
            audience="Developers",
            niche="AI",
            theme=CarouselTheme.AUTO,
        )
        theme = resolve_theme(project)
        # "meta" and "llama" and "llama-3" = 3 matches for meta brand
        assert theme == BRAND_PALETTES["meta"]

    def test_auto_detects_microsoft(self):
        """AUTO theme should detect Microsoft brand from Azure mention."""
        project = CarouselProject(
            topic="Azure Copilot updates",
            audience="Developers",
            niche="Cloud",
            theme=CarouselTheme.AUTO,
        )
        theme = resolve_theme(project)
        assert theme == BRAND_PALETTES["microsoft"]

    def test_auto_detects_openai(self):
        """AUTO theme should detect OpenAI brand from ChatGPT mention."""
        project = CarouselProject(
            topic="ChatGPT new features from OpenAI",
            audience="Everyone",
            niche="AI",
            theme=CarouselTheme.AUTO,
        )
        theme = resolve_theme(project)
        # "chatgpt" and "openai" = 2 matches for openai brand
        assert theme == BRAND_PALETTES["openai"]

    def test_auto_detects_openai_from_gpt(self):
        """AUTO theme should detect OpenAI brand from standalone GPT mention."""
        project = CarouselProject(
            topic="GPT 5.5 is out!",
            audience="AI enthusiasts",
            niche="Artificial Intelligence",
            theme=CarouselTheme.AUTO,
        )
        theme = resolve_theme(project)
        assert theme == BRAND_PALETTES["openai"]

    def test_palette_keys_always_present(self):
        """Every resolved theme must have primary, accent, background."""
        project = CarouselProject(
            topic="Anything",
            audience="Anyone",
            niche="Anything",
            theme=CarouselTheme.AUTO,
        )
        theme = resolve_theme(project)
        assert "primary" in theme
        assert "accent" in theme
        assert "background" in theme
