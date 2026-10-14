"""The Grok Bot routine packs stay aligned with the API (AE-0360, AE-0361).

Gherkin: tests/features/autopilot_grok_bot_scout.feature
  Scenario: Example JSON matches the API schemas
Gherkin: tests/features/autopilot_carousel_defaults.feature
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag_backend.modules.autopilot.api.mapping import command_from
from rag_backend.modules.autopilot.api.schemas import TopicBatch, XSignalsBatch
from rag_backend.modules.autopilot.domain.carousel_defaults import ImageStyle
from rag_backend.modules.autopilot.domain.intake import (
    IntakeFacts,
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
    """The owner runbook says not to edit v1 and how to create the bot."""
    text = _README.read_text()
    assert "GrokBot Scout" in text
    assert "v1" in text
    assert "v2" in text
    assert "takeover" in text
    assert json.loads((_PACK / "topics.example.json").read_text())["topics"]


def test_v2_example_passes_the_carousel_rules() -> None:
    """The v2 example is accepted by intake and picks a supported style."""
    batch = TopicBatch.model_validate_json((_V2 / "topics.example.json").read_text())
    prepared = tuple(prepare(item) for item in command_from(batch).proposals)
    facts = IntakeFacts(
        allowlist=frozenset(source for item in prepared for source in item.sources),
        known_hashes={},
        carousel_topics=(),
        runs_today=0,
        daily_cap=1,
    )
    plan = plan_intake(prepared, facts)
    assert plan.rejected == ()
    assert prepared[0].image_style == ImageStyle.NEO_ANIME
    assert prepared[0].image_guidance is not None
    assert "Background:" in prepared[0].image_guidance


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
    for style in ImageStyle:
        assert f"`{style.value}`" in text
