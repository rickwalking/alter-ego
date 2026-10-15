"""Carousel-default rules for GrokBot topics (AE-0361).

Gherkin: tests/features/autopilot_carousel_defaults.feature
"""

from __future__ import annotations

import pytest

from rag_backend.domain.constants import (
    IMAGE_MODEL_OPENAI,
    SUPPORTED_IMAGE_COMBOS,
    VALID_IMAGE_STYLES,
)
from rag_backend.modules.autopilot.carousel_constants import (
    REASON_AUDIENCE_NOT_SIMPLE,
    REASON_BRIEF_NOT_SIMPLE,
    REASON_BRIEF_OFF_THEME,
    REASON_IMAGE_STYLE_UNSUPPORTED,
    REASON_NICHE_NOT_SIMPLE,
    SIMPLE_BRIEF_MAX_CHARS,
)
from rag_backend.modules.autopilot.constants import (
    DEFAULT_DAILY_CAP,
    REASON_URL_IN_TEXT,
)
from rag_backend.modules.autopilot.domain.carousel_defaults import (
    DEFAULT_IMAGE_STYLE,
    SCOUT_IMAGE_STYLES,
    CarouselText,
    GuidanceRequest,
    brief_on_theme,
    carousel_reason,
    image_guidance_for,
    is_simple,
    is_supported_style,
    profile_line,
    theme_keywords,
    with_profile,
)
from rag_backend.modules.autopilot.domain.intake import (
    IntakeFacts,
    ProposalInput,
    plan_intake,
    prepare,
)

_URL = "https://news.ycombinator.com/item?id=1"
_ANIME = (
    "Futuristic anime in the style of Akira, Ghost in the Shell and "
    "Neon Genesis Evangelion. Background: ai-themed setting."
)
_NEUTRAL = (
    "Clean visuals that follow the chosen image style. "
    "Background: benchmarks-themed setting."
)


def _text(**changes: str) -> CarouselText:
    fields = {
        "title": "Agents that ship",
        "audience": "developers",
        "niche": "AI agents",
        "brief": "Why agents that ship matter for builders.",
        "image_style": "neo_anime",
    }
    fields.update(changes)
    return CarouselText(**fields)


def _input(title: str, **changes: str | None) -> ProposalInput:
    proposal = ProposalInput(
        title=title,
        angle="operator view",
        why_viral="three launches in one week",
        audience="developers",
        niche="ai",
        brief=f"A plain brief about {title}.",
        sources=(_URL,),
        score=80,
    )
    fields = {**proposal.__dict__, **changes}
    return ProposalInput(**fields)


def _facts() -> IntakeFacts:
    return IntakeFacts(
        allowlist=frozenset({_URL}),
        known_hashes={},
        carousel_topics=(),
        runs_today=0,
        daily_cap=DEFAULT_DAILY_CAP,
    )


def test_scout_styles_match_the_openai_combos_exactly() -> None:
    """Parity (AE-0361 F4): the scout's presets are derived, never hardcoded.

    Every OpenAI combo in ``SUPPORTED_IMAGE_COMBOS`` is a scout style and
    nothing else is, so a new editorial preset cannot drift from intake.
    """
    openai_styles = {
        style for model, style in SUPPORTED_IMAGE_COMBOS if model == IMAGE_MODEL_OPENAI
    }
    # AE-0376: the POV preset needs the owner's photo; the Radar IA scout
    # never picks it.
    assert openai_styles - {"pov_editorial"} == SCOUT_IMAGE_STYLES
    assert "pov_editorial" in openai_styles
    assert SCOUT_IMAGE_STYLES <= VALID_IMAGE_STYLES
    assert DEFAULT_IMAGE_STYLE == "flat_editorial"
    assert DEFAULT_IMAGE_STYLE in SCOUT_IMAGE_STYLES
    for style in SCOUT_IMAGE_STYLES:
        assert is_supported_style(style)
    assert not is_supported_style("watercolor")
    assert not is_supported_style("gemini")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("developers", True),
        ("tech founders", True),
        ("AI tool builders", True),
        ("Brazilian developers who build", False),
        ("", False),
        ("   ", False),
    ],
)
def test_simple_words_are_one_to_three_words(value: str, expected: bool) -> None:
    """Scenario Outline: Audience or niche that is not simple is rejected."""
    assert is_simple(value) is expected


def test_theme_keywords_drop_stop_words() -> None:
    assert theme_keywords("The future of AI agents") == frozenset({
        "future",
        "ai",
        "agents",
    })


def test_brief_on_theme_matches_a_title_keyword_case_insensitively() -> None:
    """Scenario: A brief that misses the theme is rejected."""
    assert brief_on_theme("GPU prices crash", "Why gpu buyers should wait.")
    assert not brief_on_theme("GPU prices crash", "Cooking recipes for the week.")
    assert not brief_on_theme("The GPU", "The week in cooking.")
    assert brief_on_theme("What is this", "Anything at all.")


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"image_style": "watercolor"}, REASON_IMAGE_STYLE_UNSUPPORTED),
        ({"audience": "people who like AI a lot"}, REASON_AUDIENCE_NOT_SIMPLE),
        ({"niche": "AI agents for enterprise workflows"}, REASON_NICHE_NOT_SIMPLE),
        (
            {"brief": "agents " + "x" * SIMPLE_BRIEF_MAX_CHARS},
            REASON_BRIEF_NOT_SIMPLE,
        ),
        ({"brief": "Cooking recipes for the week."}, REASON_BRIEF_OFF_THEME),
    ],
)
def test_carousel_reason_names_the_broken_rule(
    changes: dict[str, str], reason: str
) -> None:
    assert carousel_reason(_text(**changes)) == reason


def test_carousel_reason_accepts_a_simple_on_theme_proposal() -> None:
    assert carousel_reason(_text()) is None
    brief = "agents " + "x" * (SIMPLE_BRIEF_MAX_CHARS - len("agents "))
    assert len(brief) == SIMPLE_BRIEF_MAX_CHARS
    assert carousel_reason(_text(brief=brief)) is None


def test_template_guidance_for_neo_anime() -> None:
    """Scenario: Default neo_anime style and template guidance."""
    request = GuidanceRequest(image_style="neo_anime", niche="ai", image_guidance=None)
    assert image_guidance_for(request) == _ANIME


def test_template_guidance_for_other_styles_is_style_neutral() -> None:
    """Scenario: Non-anime style gets style-neutral template guidance."""
    request = GuidanceRequest(
        image_style="flat_editorial",
        niche="benchmarks",
        image_guidance=None,
    )
    assert image_guidance_for(request) == _NEUTRAL


def test_scout_guidance_wins_over_the_template() -> None:
    """Scenario: A bot-chosen style is accepted."""
    guidance = "Product photo. Background: a chip fab clean room."
    request = GuidanceRequest(
        image_style="hyperreal", niche="chips", image_guidance=guidance
    )
    assert image_guidance_for(request) == guidance
    empty = GuidanceRequest(image_style="hyperreal", niche="chips", image_guidance="")
    assert image_guidance_for(empty).endswith("Background: chips-themed setting.")


def test_profile_line_and_review_body() -> None:
    """Scenario: The owner review message shows audience, niche and style."""
    line = profile_line("developers", "AI agents", "neo_anime")
    assert line == "Audience: developers · Niche: AI agents · Style: neo_anime"
    assert with_profile(line, "caption") == f"{line}\n\ncaption"
    assert profile_line("", "", "") == ""
    assert with_profile("", "caption") == "caption"
    assert profile_line("", "", "cinematic").endswith("Style: cinematic")


def test_prepare_strips_guidance_and_drops_blank_guidance() -> None:
    padded = prepare(_input("Agents", image_guidance="  Anime.\x00  "))
    blank = prepare(_input("Agents", image_guidance="\x00 "))
    absent = prepare(_input("Agents"))
    assert padded.image_guidance == "Anime."
    assert blank.image_guidance is None
    assert absent.image_guidance is None
    assert absent.image_style == "flat_editorial"


def test_plan_rejects_only_the_proposal_that_breaks_a_rule() -> None:
    """Scenario Outline: Audience or niche that is not simple is rejected."""
    wordy = prepare(_input("Agents", audience="Brazilian developers who build AI"))
    good = prepare(_input("Robots", image_style="cinematic"))
    plan = plan_intake((wordy, good), _facts())
    assert [(item.title, item.reason) for item in plan.rejected] == [
        ("Agents", REASON_AUDIENCE_NOT_SIMPLE)
    ]
    assert len(plan.new_candidates) == 1
    assert plan.new_candidates[0].proposal.image_style == "cinematic"
    assert plan.new_candidates[0].queue


def test_plan_rejects_only_the_topic_with_an_unsupported_style() -> None:
    """Scenario: An unsupported style rejects only that topic (AE-0361 F2)."""
    bad = prepare(_input("Agents", image_style="watercolor"))
    good = prepare(_input("Robots", image_style="cinematic"))
    plan = plan_intake((bad, good), _facts())
    assert [(item.title, item.reason) for item in plan.rejected] == [
        ("Agents", REASON_IMAGE_STYLE_UNSUPPORTED)
    ]
    assert [item.proposal.title for item in plan.new_candidates] == ["Robots"]


def test_plan_rejects_a_url_in_the_image_guidance() -> None:
    """Scenario: A URL in the image guidance is rejected."""
    proposal = prepare(_input("Agents", image_guidance="See www.example.com"))
    plan = plan_intake((proposal,), _facts())
    assert [item.reason for item in plan.rejected] == [REASON_URL_IN_TEXT]
