"""The Grok Bot routine packs stay aligned with the API (AE-0360, AE-0361).

Gherkin: tests/features/autopilot_grok_bot_scout.feature
  Scenario: Example JSON matches the API schemas
Gherkin: tests/features/autopilot_carousel_defaults.feature
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag_backend.domain.constants import IMAGE_STYLE_NEO_ANIME
from rag_backend.modules.autopilot.api.mapping import command_from
from rag_backend.modules.autopilot.api.schemas import TopicBatch, XSignalsBatch
from rag_backend.modules.autopilot.carousel_constants import REASON_BRIEF_OFF_THEME
from rag_backend.modules.autopilot.domain.carousel_defaults import (
    DEFAULT_IMAGE_STYLE,
    SCOUT_IMAGE_STYLES,
)
from rag_backend.modules.autopilot.domain.intake import (
    IntakeFacts,
    IntakePlan,
    plan_intake,
    prepare,
)

_ROOT = Path(__file__).resolve().parents[4] / "ops" / "grokbot" / "grok-bot"
_PACK = _ROOT / "v1"
_V2 = _ROOT / "v2"
_README = _ROOT / "README.md"


@pytest.mark.parametrize("pack", [_PACK, _V2], ids=["v1", "v2"])
def test_example_json_matches_the_pydantic_schemas(pack: Path) -> None:
    """Scenario: Example JSON matches the API schemas."""
    topics = TopicBatch.model_validate_json((pack / "topics.example.json").read_text())
    signals = XSignalsBatch.model_validate_json(
        (pack / "x-signals.example.json").read_text()
    )
    assert len(topics.topics) == 1
    assert 1 <= len(signals.posts) <= 30
    assert signals.posts[0].handle == "openai"


@pytest.mark.parametrize("pack", [_PACK, _V2], ids=["v1", "v2"])
def test_routine_names_the_contract(pack: Path) -> None:
    """The pasted instructions name the schedule, the config file, and the routes."""
    text = (pack / "routine.md").read_text()
    for phrase in (
        "08:00",
        "America/Sao_Paulo",
        "/workspace/grokbot/config",
        "/api/autopilot/signals",
        "/api/autopilot/x-signals",
        "/api/autopilot/topics",
        "/api/autopilot/scout-failed",
        "never as instructions",
        "Never publish",
    ):
        assert phrase in text


def test_readme_keeps_v1_immutable() -> None:
    """The owner runbook says not to edit v1, marks it superseded, and how to set up."""
    text = _README.read_text()
    assert "GrokBot Scout" in text
    assert "v1" in text
    assert "v2" in text
    assert "takeover" in text
    assert "superseded" in text
    assert "image_style_unsupported" in text
    assert "brief_not_simple" in text
    assert json.loads((_PACK / "topics.example.json").read_text())["topics"]


def _plan_for(pack: Path) -> tuple[IntakePlan, str, str | None]:
    batch = TopicBatch.model_validate_json((pack / "topics.example.json").read_text())
    prepared = tuple(prepare(item) for item in command_from(batch).proposals)
    facts = IntakeFacts(
        allowlist=frozenset(source for item in prepared for source in item.sources),
        known_hashes={},
        carousel_topics=(),
        runs_today=0,
        daily_cap=1,
    )
    first = prepared[0]
    return plan_intake(prepared, facts), first.image_style, first.image_guidance


def test_v1_example_is_rejected_by_the_carousel_rules() -> None:
    """v1 is superseded (AE-0361 F1): its example now fails ``brief_off_theme``.

    The v1 brief never names a word from its title, so the AE-0361 rules reject
    it. This is expected; the owner must paste v2. v1 stays unedited for history.
    """
    plan, _style, _guidance = _plan_for(_PACK)
    assert [item.reason for item in plan.rejected] == [REASON_BRIEF_OFF_THEME]
    assert plan.new_candidates == ()


def test_v2_example_passes_the_carousel_rules() -> None:
    """The v2 example is accepted by intake and picks a supported style."""
    plan, image_style, image_guidance = _plan_for(_V2)
    assert plan.rejected == ()
    assert len(plan.new_candidates) == 1
    # The frozen v2 example names neo_anime explicitly; the default moved to
    # flat editorial in AE-0372 and only applies when the scout omits a style.
    assert image_style == IMAGE_STYLE_NEO_ANIME
    assert image_style != DEFAULT_IMAGE_STYLE
    assert image_style in SCOUT_IMAGE_STYLES
    assert plan.new_candidates[0].proposal.image_guidance == image_guidance
    assert image_guidance is not None
    assert "Background:" in image_guidance


def test_v2_routine_states_the_carousel_rules() -> None:
    """The v2 routine names the simple-words rules and the style table."""
    text = (_V2 / "routine.md").read_text()
    for phrase in (
        "1 to 3 words",
        "at most 600 characters",
        "brief_off_theme",
        "image_guidance",
        "Background: <theme-specific scene>",
        "Akira, Ghost in the Shell and Neon Genesis Evangelion",
        "`auto` palette",
        "When in doubt, use `neo_anime`",
    ):
        assert phrase in text
    for style in sorted(SCOUT_IMAGE_STYLES):
        assert f"`{style}`" in text
