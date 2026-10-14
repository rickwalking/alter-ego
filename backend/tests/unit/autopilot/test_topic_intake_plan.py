"""Pure topic-intake decisions (AE-0353).

Gherkin: tests/features/autopilot_topic_intake.feature
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.autopilot.constants import (
    DEFAULT_DAILY_CAP,
    REASON_DAILY_CAP_REACHED,
    REASON_DUPLICATE_TOPIC,
    REASON_EMPTY_TEXT,
    REASON_SOURCE_NOT_IN_SIGNALS,
    REASON_URL_IN_TEXT,
)
from rag_backend.modules.autopilot.domain.intake import (
    IntakeFacts,
    ProposalInput,
    plan_intake,
    prepare,
)
from rag_backend.modules.autopilot.domain.topic_text import (
    contains_url,
    sao_paulo_day,
    signal_hash,
    strip_controls,
    titles_are_duplicates,
)

_URL_A = "https://news.ycombinator.com/item?id=1"
_URL_B = "https://huggingface.co/papers/1"
_FOREIGN = "https://evil.example/invented"
_BRIEF = "A plain brief about agents."
_BRIEF_TEMPLATE = "A plain brief about {title}."


def _brief_for(title: str, brief: str | None) -> str:
    """AE-0361: the default brief names the title, so it stays on theme."""
    if brief is not None:
        return brief
    return _BRIEF_TEMPLATE.format(title=title)


def _input(
    title: str,
    url: str,
    score: int,
    *,
    brief: str | None = None,
) -> ProposalInput:
    return ProposalInput(
        title=title,
        angle="operator view",
        why_viral="three launches in one week",
        audience="builders",
        niche="ai",
        brief=_brief_for(title, brief),
        sources=(url,),
        score=score,
    )


def _facts(
    *,
    known_hashes: dict[str, UUID] | None = None,
    carousel_topics: tuple[str, ...] = (),
    runs_today: int = 0,
    daily_cap: int = DEFAULT_DAILY_CAP,
) -> IntakeFacts:
    hashes: dict[str, UUID] = {} if known_hashes is None else known_hashes
    return IntakeFacts(
        allowlist=frozenset({_URL_A, _URL_B}),
        known_hashes=hashes,
        carousel_topics=carousel_topics,
        runs_today=runs_today,
        daily_cap=daily_cap,
    )


def test_signal_hash_ignores_source_order_and_title_case() -> None:
    left = signal_hash(
        "Hello  World",
        ("https://News.Ycombinator.com/item/", _URL_B),
    )
    right = signal_hash(
        "hello world",
        (_URL_B, "https://news.ycombinator.com/item"),
    )
    assert left == right


def test_control_characters_are_stripped_before_the_hash() -> None:
    # Scenario: Control characters are stripped
    dirty = prepare(_input("Agents\x00 that ship", _URL_A, 80))
    clean = prepare(_input("Agents that ship", _URL_A, 80))
    assert dirty.title == "Agents that ship"
    assert "\x00" not in dirty.title
    assert dirty.signal_hash == clean.signal_hash
    assert strip_controls("a\x00b\n") == "ab"
    assert not contains_url("http is not a url")
    assert contains_url("see https://evil.example/x")


def test_jaccard_threshold_is_inclusive() -> None:
    assert titles_are_duplicates("alpha beta gamma delta", "alpha beta gamma epsilon")
    assert not titles_are_duplicates(
        "alpha beta gamma delta epsilon",
        "alpha beta gamma xray yankee",
    )


def test_sao_paulo_midnight_starts_the_cap_day() -> None:
    # 02:30 UTC is still 23:30 the previous day in Sao Paulo (UTC-3).
    before = datetime(2026, 10, 13, 2, 30, tzinfo=UTC)
    after = datetime(2026, 10, 13, 3, 0, tzinfo=UTC)
    before_start, before_end = sao_paulo_day(before)
    after_start, _after_end = sao_paulo_day(after)
    assert before_start == datetime(2026, 10, 12, 3, 0, tzinfo=UTC)
    assert before_end == after_start
    assert after_start == datetime(2026, 10, 13, 3, 0, tzinfo=UTC)
    assert before < before_end
    assert after >= after_start


def test_best_score_is_the_only_queued_candidate() -> None:
    # Scenario: Best valid topic is queued
    low = prepare(_input("Quiet launch", _URL_B, 70))
    high = prepare(_input("Agents that ship", _URL_A, 90))
    plan = plan_intake((low, high), _facts())
    queued = [item for item in plan.new_candidates if item.queue]
    stored = [item for item in plan.new_candidates if not item.queue]
    assert plan.rejected == ()
    assert len(plan.accepted_ids) == 2
    assert len(queued) == 1
    assert queued[0].proposal.score == 90
    assert stored[0].proposal.score == 70


def test_foreign_url_rejects_only_that_proposal() -> None:
    # Scenario: Invented source is rejected
    # Scenario: A foreign URL rejects only that proposal
    bad = prepare(_input("Invented", _FOREIGN, 99))
    good = prepare(_input("Grounded", _URL_A, 40))
    plan = plan_intake((bad, good), _facts())
    assert [item.reason for item in plan.rejected] == [REASON_SOURCE_NOT_IN_SIGNALS]
    assert len(plan.new_candidates) == 1
    assert plan.new_candidates[0].queue is True


def test_daily_cap_stores_the_candidate_and_queues_nothing() -> None:
    # Scenario: Daily cap
    proposal = prepare(_input("Another one", _URL_A, 88))
    plan = plan_intake((proposal,), _facts(runs_today=1))
    assert len(plan.new_candidates) == 1
    assert plan.new_candidates[0].queue is False
    assert plan.accepted_ids == (plan.new_candidates[0].candidate_id,)
    assert plan.rejected[0].reason == REASON_DAILY_CAP_REACHED


def test_known_hash_is_not_inserted_again() -> None:
    # Scenario: Replay is idempotent
    proposal = prepare(_input("Agents that ship", _URL_A, 90))
    existing = uuid4()
    plan = plan_intake(
        (proposal, proposal), _facts(known_hashes={proposal.signal_hash: existing})
    )
    assert plan.accepted_ids == (existing,)
    assert plan.new_candidates == ()
    assert plan.rejected == ()


def test_url_in_free_text_is_rejected() -> None:
    # Scenario: URL in free text is rejected
    proposal = prepare(_input("Agents", _URL_A, 80, brief="See https://evil.example/x"))
    plan = plan_intake((proposal,), _facts())
    assert plan.new_candidates == ()
    assert plan.rejected[0].reason == REASON_URL_IN_TEXT


def test_blank_title_after_stripping_is_rejected() -> None:
    proposal = prepare(_input("\x00", _URL_A, 80))
    plan = plan_intake((proposal,), _facts())
    assert plan.rejected[0].reason == REASON_EMPTY_TEXT
    assert plan.new_candidates == ()


def test_recent_carousel_title_is_a_duplicate() -> None:
    # Scenario: Recent carousel topic is a duplicate
    proposal = prepare(_input("alpha beta gamma delta", _URL_A, 80))
    facts = _facts(carousel_topics=("alpha beta gamma epsilon",))
    plan = plan_intake((proposal,), facts)
    assert plan.rejected[0].reason == REASON_DUPLICATE_TOPIC
    assert plan.new_candidates == ()


def test_higher_cap_queues_both() -> None:
    # Scenario: A higher daily cap queues more than one run
    first = prepare(_input("One", _URL_A, 60))
    second = prepare(_input("Two", _URL_B, 70))
    plan = plan_intake((first, second), _facts(daily_cap=2))
    assert sum(item.queue for item in plan.new_candidates) == 2
    assert plan.rejected == ()


def test_served_url_cutoff_is_six_hours() -> None:
    from rag_backend.modules.autopilot.domain.topic_text import served_url_cutoff

    moment = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)
    assert served_url_cutoff(moment) == moment - timedelta(hours=6)


def test_settings_default_cap_matches_the_module_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTOPILOT_DAILY_CAP", raising=False)
    get_settings.cache_clear()
    try:
        assert get_settings().autopilot_daily_cap == DEFAULT_DAILY_CAP
    finally:
        get_settings.cache_clear()
