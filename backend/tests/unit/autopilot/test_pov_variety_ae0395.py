"""POV art style and palette rotation for autopilot carousels.

Gherkin: tests/features/autopilot_variety_ae0395.feature and
tests/features/autopilot_pov_thesis.feature ("POV point-slide art follows the
scout's explicit style").
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from rag_backend.domain.constants.carousel_themes import CAROUSEL_THEMES
from rag_backend.modules.autopilot.application.run_spec import pov_image_style
from rag_backend.modules.autopilot.domain.carousel_defaults import (
    AUTOPILOT_THEME_ROTATION,
    rotated_theme,
)
from rag_backend.modules.autopilot.domain.models import TopicCandidate

pytestmark = pytest.mark.unit

_LIGHT_BACKGROUND_MIN = 0xC0


def _topic(image_style: str) -> TopicCandidate:
    from uuid import uuid4

    return TopicCandidate(
        candidate_id=uuid4(),
        title="Seu time de agentes de IA",
        angle="a",
        why_viral="w",
        audience="devs",
        niche="IA",
        brief="b",
        sources=(),
        score=80,
        signal_hash="h",
        status="accepted",
        image_style=image_style,
        content_mode="pov",
    )


# Scenario Outline: POV point-slide art follows the scout's explicit style
@pytest.mark.parametrize(
    ("style", "preset"),
    [
        ("flat_editorial", "neo_anime"),
        ("cinematic", "cinematic"),
        ("unknown_style", "neo_anime"),
        ("neo_anime", "neo_anime"),
    ],
)
def test_pov_image_style(style: str, preset: str) -> None:
    assert pov_image_style(_topic(style)) == preset


# Scenario: Consecutive days get different palettes
def test_consecutive_days_get_different_dark_palettes() -> None:
    day = datetime(2026, 10, 17, 15, 0, tzinfo=UTC)
    first, second = rotated_theme(day), rotated_theme(day + timedelta(days=1))
    assert first != second
    for key in (first, second):
        background = CAROUSEL_THEMES[key]["background"]
        assert int(background[1:3], 16) < _LIGHT_BACKGROUND_MIN


def test_every_rotation_theme_exists_and_is_dark() -> None:
    for key in AUTOPILOT_THEME_ROTATION:
        assert int(CAROUSEL_THEMES[key]["background"][1:3], 16) < _LIGHT_BACKGROUND_MIN


# Scenario: The day follows São Paulo, not UTC
def test_the_day_follows_sao_paulo() -> None:
    """02:30 UTC on 10-18 is still 23:30 on 10-17 in São Paulo."""
    late_sp = datetime(2026, 10, 18, 2, 30, tzinfo=UTC)
    same_sp_day = datetime(2026, 10, 17, 15, 0, tzinfo=UTC)
    assert rotated_theme(late_sp) == rotated_theme(same_sp_day)


# Scenario: The overused blue/amber theme is not in the rotation
def test_overused_theme_is_not_rotated() -> None:
    assert "ai_competition" not in AUTOPILOT_THEME_ROTATION
    assert len(set(AUTOPILOT_THEME_ROTATION)) == len(AUTOPILOT_THEME_ROTATION)


def test_topic_helper_is_frozen() -> None:
    topic = _topic("cinematic")
    assert replace(topic, image_style="neo_anime").image_style == "neo_anime"
