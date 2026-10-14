"""The Grok Bot routine pack stays aligned with the API (AE-0360).

Gherkin: tests/features/autopilot_grok_bot_scout.feature
  Scenario: Example JSON matches the API schemas
"""

from __future__ import annotations

import json
from pathlib import Path

from rag_backend.modules.autopilot.api.schemas import TopicBatch, XSignalsBatch

_PACK = Path(__file__).resolve().parents[4] / "ops" / "grokbot" / "grok-bot" / "v1"
_README = _PACK.parent / "README.md"


def test_example_json_matches_the_pydantic_schemas() -> None:
    """Scenario: Example JSON matches the API schemas."""
    topics = TopicBatch.model_validate_json((_PACK / "topics.example.json").read_text())
    signals = XSignalsBatch.model_validate_json(
        (_PACK / "x-signals.example.json").read_text()
    )
    assert len(topics.topics) == 1
    assert 1 <= len(signals.posts) <= 30
    assert signals.posts[0].handle == "openai"


def test_routine_names_the_contract() -> None:
    """The pasted instructions name the schedule, the config file, and the routes."""
    text = (_PACK / "routine.md").read_text()
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
