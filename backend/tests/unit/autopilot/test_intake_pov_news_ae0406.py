"""Topic intake with ``pov_news`` topics and quotes (AE-0406, spec §3-§6).

Gherkin: tests/features/autopilot_pov_news_ae0406.feature
"""

from __future__ import annotations

from dataclasses import replace

from rag_backend.modules.autopilot.domain.intake import (
    IntakeFacts,
    IntakePlan,
    ProposalInput,
    TopicRejection,
    plan_intake,
    prepare,
)
from rag_backend.modules.autopilot.domain.pov_choice import PovChoice
from tests.unit.autopilot.news_quote_support import (
    OTHER_URL,
    POST_TEXT,
    POST_URL,
    news_proposal,
    quote,
)


def _facts(news_runs_this_week: int = 0, runs_today: int = 0) -> IntakeFacts:
    return IntakeFacts(
        allowlist=frozenset({POST_URL, OTHER_URL}),
        known_hashes={},
        carousel_topics=(),
        runs_today=runs_today,
        daily_cap=3,
        news_runs_this_week=news_runs_this_week,
        post_texts={POST_URL: POST_TEXT},
    )


def _plan(*proposals: ProposalInput, facts: IntakeFacts | None = None) -> IntakePlan:
    prepared = tuple(prepare(item) for item in proposals)
    return plan_intake(prepared, facts or _facts())


def _radar(index: int = 0, title: str = "Radar sobre agentes") -> ProposalInput:
    return replace(
        news_proposal(index=index, title=title),
        content_mode="news_analysis",
        thesis_draft=None,
    )


# Scenario: A pov_news topic with one verified quote is accepted and queued
def test_verified_quote_is_accepted_queued_and_kept() -> None:
    plan = _plan(news_proposal(quote()))
    assert plan.rejected == ()
    assert len(plan.accepted_ids) == 1
    (candidate,) = plan.new_candidates
    assert candidate.queue is True
    assert candidate.proposal.quotes == (quote(),)


# Scenario: A pov_news topic without quotes is accepted
def test_pov_news_without_quotes_is_accepted() -> None:
    plan = _plan(news_proposal())
    assert plan.rejected == ()
    assert plan.new_candidates[0].proposal.quotes == ()


# Scenario Outline: A quote problem rejects only that topic
def test_a_quote_problem_rejects_only_its_topic() -> None:
    bad = news_proposal(quote(excerpt="invented words"), index=1, title="Outro tema")
    plan = _plan(news_proposal(quote()), bad)
    assert len(plan.accepted_ids) == 1
    assert plan.rejected == (
        TopicRejection(
            title="Outro tema",
            reason="quote_not_in_post",
            index=1,
            field="quotes[0].excerpt",
        ),
    )


def test_a_post_never_sent_through_x_signals_is_a_source_problem() -> None:
    facts = replace(_facts(), post_texts={})
    plan = _plan(news_proposal(quote()), facts=facts)
    assert plan.rejected[0].reason == "quote_source_invalid"
    assert plan.rejected[0].field == "quotes[0].url"


# Scenario: Quotes on a pov topic are refused
def test_quotes_on_a_pov_topic_are_refused() -> None:
    pov = replace(news_proposal(quote()), content_mode="pov")
    plan = _plan(pov)
    assert plan.rejected[0].reason == "quote_invalid"
    assert plan.rejected[0].field == "quotes"


def test_quotes_on_a_radar_topic_are_refused() -> None:
    plan = _plan(replace(_radar(), quotes=(quote(),)))
    assert (plan.rejected[0].reason, plan.rejected[0].field) == (
        "quote_invalid",
        "quotes",
    )


# Scenario: pov_news needs a thesis draft and ignores pov_format
def test_pov_news_without_thesis_is_thesis_missing() -> None:
    plan = _plan(replace(news_proposal(), thesis_draft=None))
    assert (plan.rejected[0].reason, plan.rejected[0].field) == (
        "thesis_missing",
        "thesis_draft",
    )


def test_pov_news_ignores_the_format_but_keeps_the_slide_count() -> None:
    choice = PovChoice(pov_format="comparacao", slide_count=10)
    prepared = prepare(replace(news_proposal(), pov_choice=choice))
    assert prepared.pov_choice == PovChoice(pov_format=None, slide_count=10)


def test_pov_keeps_its_format() -> None:
    choice = PovChoice(pov_format="comparacao", slide_count=10)
    prepared = prepare(replace(news_proposal(), content_mode="pov", pov_choice=choice))
    assert prepared.pov_choice == choice


# Scenario: pov_news counts toward the daily cap only
def test_pov_news_is_not_a_radar_run() -> None:
    assert prepare(news_proposal()).is_news is False
    assert prepare(_radar()).is_news is True


def test_pov_news_is_queued_when_this_weeks_radar_run_is_used() -> None:
    plan = _plan(news_proposal(), _radar(index=1), facts=_facts(news_runs_this_week=1))
    queued = [item for item in plan.new_candidates if item.queue]
    assert [item.proposal.content_mode for item in queued] == ["pov_news"]
    assert [(r.reason, r.index) for r in plan.rejected] == [
        ("weekly_news_cap_reached", 1)
    ]


def test_pov_news_counts_toward_the_daily_cap() -> None:
    plan = _plan(news_proposal(), facts=_facts(runs_today=3))
    assert plan.new_candidates[0].queue is False
    assert [(r.reason, r.index, r.field) for r in plan.rejected] == [
        ("daily_cap_reached", 0, None)
    ]


# Scenario Outline: Topics without pov_news behave as today (index and field)
def test_rejections_carry_index_and_the_field_that_caused_them() -> None:
    proposals = (
        replace(_radar(index=0, title="Primeiro"), audience="many words in here"),
        replace(_radar(index=1, title="Segundo"), niche="a b c d"),
        replace(_radar(index=2, title="Terceiro"), image_style="unknown_style"),
    )
    plan = _plan(*proposals)
    assert [(r.index, r.reason, r.field) for r in plan.rejected] == [
        (0, "audience_not_simple", "audience"),
        (1, "niche_not_simple", "niche"),
        (2, "image_style_unsupported", "image_style"),
    ]


def test_brief_rules_name_the_brief() -> None:
    plan = _plan(replace(_radar(), brief="x" * 601))
    assert (plan.rejected[0].reason, plan.rejected[0].field) == (
        "brief_not_simple",
        "brief",
    )
    off = _plan(replace(_radar(), brief="Nada a ver com nada."))
    assert (off.rejected[0].reason, off.rejected[0].field) == (
        "brief_off_theme",
        "brief",
    )


def test_text_rules_name_the_field() -> None:
    blank = _plan(replace(_radar(), why_viral="\x00"))
    assert (blank.rejected[0].reason, blank.rejected[0].field) == (
        "empty_text",
        "why_viral",
    )
    linked = _plan(replace(news_proposal(), thesis_draft="veja www.example.com"))
    assert (linked.rejected[0].reason, linked.rejected[0].field) == (
        "url_in_text",
        "thesis_draft",
    )


def test_a_foreign_source_names_its_position() -> None:
    plan = _plan(replace(_radar(), sources=(POST_URL, "https://evil.example/x")))
    assert (plan.rejected[0].reason, plan.rejected[0].field) == (
        "source_not_in_signals",
        "sources[1]",
    )


def test_a_duplicate_title_carries_the_index_without_field() -> None:
    facts = replace(_facts(), carousel_topics=("Radar sobre agentes",))
    plan = _plan(_radar(index=4), facts=facts)
    assert [(r.index, r.reason, r.field) for r in plan.rejected] == [
        (4, "duplicate_topic", None)
    ]
