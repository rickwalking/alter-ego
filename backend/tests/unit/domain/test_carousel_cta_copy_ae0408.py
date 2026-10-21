"""The CTA copy never promises a weekday schedule (owner feedback, be190a0c)."""

from __future__ import annotations

import pytest

from rag_backend.domain.constants.carousel_cta import (
    CTA_COPY_EN,
    CTA_COPY_PT,
    CTA_GOAL_FOLLOW,
)

_WEEKDAYS = (
    "segunda",
    "terça",
    "quarta",
    "quinta",
    "sexta",
    "sábado",
    "domingo",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


@pytest.mark.parametrize("copy", [*CTA_COPY_PT.values(), *CTA_COPY_EN.values()])
def test_no_cta_copy_names_a_weekday(copy: str) -> None:
    """Scenario: no CTA variant, PT or EN, mentions a day of the week."""
    lowered = copy.lower()
    assert not any(day in lowered for day in _WEEKDAYS), copy


def test_follow_cta_keeps_the_handle_and_the_promise() -> None:
    """Scenario: the follow CTA still names the handle and what the creator delivers."""
    pt = CTA_COPY_PT[CTA_GOAL_FOLLOW].format(handle="@pedromarins.ai")
    en = CTA_COPY_EN[CTA_GOAL_FOLLOW].format(handle="@pedromarins.ai")
    assert pt == "Siga @pedromarins.ai: eu traduzo IA em decisões reais."
    assert en == "Follow @pedromarins.ai: I turn AI into real decisions."
