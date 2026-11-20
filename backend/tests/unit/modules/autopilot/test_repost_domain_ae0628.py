"""Repost draft rules, hashing, the key, callbacks, publish time and copy.

Gherkin: tests/features/autopilot_repost_drafts_ae0628.feature
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.domain.recommend import (
    RecommendQuery,
    ScheduleSignals,
    slots_on,
)
from rag_backend.modules.autopilot.domain.repost import (
    PublishWindow,
    RepostError,
    parse_idempotency_key,
    parse_repost_callback,
    request_hash,
)
from rag_backend.modules.autopilot.domain.repost_copy import (
    ApprovalNotice,
    approval_keyboard,
    approval_text,
    approved_text,
    metrics_line,
)
from rag_backend.modules.autopilot.domain.repost_rules import (
    EligibilityFacts,
    check_caption,
    check_eligibility,
    check_fields,
    check_final_length,
    cover_usable,
)
from rag_backend.modules.autopilot.domain.repost_schedule import (
    PublishTimeQuery,
    publish_time,
)
from rag_backend.modules.autopilot.domain.schedule import schedule_zone
from rag_backend.modules.autopilot.repost_constants import (
    ERR_ALREADY_REPOSTED,
    ERR_ASSET_INVALID,
    ERR_INVALID_FIELD,
    ERR_REEL_NOT_FOUND,
    ERR_TOO_RECENT,
    ERR_WEEKLY_CAP,
    MESSAGE_BY_CODE,
)
from tests.unit.modules.autopilot.repost_fakes import (
    NOW,
    draft,
    reel,
    reel_cover,
    stored,
    window,
)


def _field_of(error: pytest.ExceptionInfo[RepostError]) -> str | None:
    assert error.value.problem.code == ERR_INVALID_FIELD
    assert error.value.problem.status == 400
    return error.value.problem.field


# Scenario Outline: Field rules answer 400 invalid_field
@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"media_id": "abc"}, "media_id"),
        ({"media_id": "1" * 33}, "media_id"),
        ({"caption": "   "}, "caption"),
        ({"caption": "x" * 2201}, "caption"),
        ({"caption": " ".join(f"#t{i}" for i in range(31))}, "caption"),
        ({"caption": " ".join(f"@u{i}" for i in range(21))}, "caption"),
        ({"hook_text": "x" * 91}, "hook_text"),
        ({"hook_duration_s": 0.0}, "hook_duration_s"),
        ({"hook_duration_s": 4.5}, "hook_duration_s"),
        ({"hook_duration_s": float("nan")}, "hook_duration_s"),
        ({"trim_start_s": -1.0}, "trim_start_s"),
        ({"trim_start_s": float("inf")}, "trim_start_s"),
        ({"trim_start_s": 5.0, "trim_end_s": 4.0}, "trim_end_s"),
        ({"trim_end_s": float("nan")}, "trim_end_s"),
        ({"reason": "too short"}, "reason"),
        ({"reason": "x" * 601}, "reason"),
        ({"collaborators": ("a", "b", "c", "d")}, "collaborators"),
        ({"collaborators": ("@bad name",)}, "collaborators"),
    ],
)
def test_field_rules(changes: dict[str, object], field: str) -> None:
    with pytest.raises(RepostError) as error:
        check_fields(draft(**changes), NOW)
    assert _field_of(error) == field


def test_valid_draft_and_edge_values_pass() -> None:
    check_fields(draft(), NOW)
    check_fields(
        draft(
            caption="x" * 2200,
            hook_text="x" * 90,
            hook_duration_s=4.0,
            collaborators=("rickwalking13", "a.b_c"),
            reason="x" * 10,
            window=window(),
        ),
        NOW,
    )
    check_caption(" ".join(f"#t{i}" for i in range(30)))
    check_caption(" ".join(f"@u{i}" for i in range(20)))


def test_email_is_not_a_mention_and_anchor_is_not_a_hashtag() -> None:
    check_caption("mail me at a@b.com " + " ".join(f"@u{i}" for i in range(20)))
    check_caption("x&#39; " + " ".join(f"#t{i}" for i in range(30)))


@pytest.mark.parametrize(
    ("win", "field"),
    [
        (
            PublishWindow(
                earliest=NOW.replace(tzinfo=None), latest=NOW + timedelta(hours=2)
            ),
            "publish_window.earliest",
        ),
        (
            PublishWindow(
                earliest=NOW, latest=(NOW + timedelta(hours=2)).replace(tzinfo=None)
            ),
            "publish_window.latest",
        ),
        (window(5, 2), "publish_window.latest"),
        (window(-5, -1), "publish_window.latest"),
    ],
)
def test_window_rules(win: PublishWindow, field: str) -> None:
    with pytest.raises(RepostError) as error:
        check_fields(draft(window=win), NOW)
    assert _field_of(error) == field


def _facts(**changes: object) -> EligibilityFacts:
    base = EligibilityFacts(
        now=NOW,
        reel=reel(),
        duration_s=60.0,
        live_repost=False,
        recent_drafts=0,
        cover=None,
    )
    return replace(base, **changes)


# Scenario: A foreign id or a non-Reel is not found
# Scenario: A Reel younger than 60 days is too recent
# Scenario: A Reel with a live repost in 90 days is refused
# Scenario: The weekly cap
@pytest.mark.parametrize(
    ("facts", "code", "status"),
    [
        (_facts(reel=None), ERR_REEL_NOT_FOUND, 404),
        (_facts(reel=reel(product="FEED")), ERR_REEL_NOT_FOUND, 404),
        (_facts(reel=reel(days_old=59)), ERR_TOO_RECENT, 422),
        (_facts(live_repost=True), ERR_ALREADY_REPOSTED, 409),
        (_facts(recent_drafts=2), ERR_WEEKLY_CAP, 422),
    ],
)
def test_eligibility_refusals(facts: EligibilityFacts, code: str, status: int) -> None:
    with pytest.raises(RepostError) as error:
        check_eligibility(draft(), facts)
    assert (error.value.problem.code, error.value.problem.status) == (code, status)
    assert error.value.message == MESSAGE_BY_CODE[code]


def test_sixty_days_and_one_recent_draft_are_eligible() -> None:
    check_eligibility(draft(), _facts(reel=reel(days_old=60), recent_drafts=1))


# Scenario: A cover must be a fresh, unused reel cover
@pytest.mark.parametrize(
    "cover",
    [
        None,
        reel_cover(purpose="carousel_cover"),
        reel_cover(kind="screenshot"),
        reel_cover(created_at=NOW - timedelta(hours=7)),
        reel_cover(repost_id=uuid4()),
        reel_cover(topic_candidate_id=uuid4()),
        reel_cover(width=1080, height=1350),
    ],
)
def test_unusable_cover_is_asset_invalid(cover: object) -> None:
    asset = uuid4()
    with pytest.raises(RepostError) as error:
        check_eligibility(draft(cover_asset_id=asset), _facts(cover=cover))
    assert error.value.problem.code == ERR_ASSET_INVALID


def test_fresh_reel_cover_is_usable() -> None:
    assert cover_usable(reel_cover(), NOW)
    check_eligibility(draft(cover_asset_id=uuid4()), _facts(cover=reel_cover()))


@pytest.mark.parametrize(
    ("changes", "duration", "field"),
    [
        ({"trim_end_s": 2.0}, 60.0, "trim_end_s"),
        ({}, 95.0, "trim_end_s"),
        ({"trim_start_s": 61.0}, 60.0, "trim_start_s"),
        ({"trim_start_s": 58.5}, 60.0, "trim_end_s"),
        ({"trim_end_s": 100.0}, None, "trim_end_s"),
    ],
)
def test_final_length_rules(
    changes: dict[str, object], duration: float | None, field: str
) -> None:
    with pytest.raises(RepostError) as error:
        check_final_length(draft(**changes), duration)
    assert _field_of(error) == field


def test_final_length_edges_pass() -> None:
    check_final_length(draft(), None)
    check_final_length(draft(), 90.0)
    check_final_length(draft(trim_end_s=3.0), 60.0)
    check_final_length(draft(trim_start_s=10.0, trim_end_s=200.0), 60.0)


def test_request_hash_ignores_the_key_but_not_the_body() -> None:
    one = draft(
        idempotency_key="aaaaaaaa",
        window=window(),
        cover_asset_id=uuid4(),
        collaborators=("x",),
    )
    assert request_hash(one) == request_hash(replace(one, idempotency_key="bbbbbbbb"))
    assert request_hash(one) != request_hash(replace(one, caption="other"))
    assert len(request_hash(draft())) == 64


@pytest.mark.parametrize("value", [None, "short", "x" * 129, "has space!!", "ç" * 10])
def test_idempotency_key_rules(value: str | None) -> None:
    with pytest.raises(RepostError) as error:
        parse_idempotency_key(value)
    assert _field_of(error) == "Idempotency-Key"


def test_idempotency_key_bounds_accepted() -> None:
    assert parse_idempotency_key("a" * 8) == "a" * 8
    assert parse_idempotency_key("A-_9" * 32) == "A-_9" * 32


def test_callback_parsing() -> None:
    repost_id = uuid4()
    for action in ("ok", "orig", "cap", "no"):
        parsed = parse_repost_callback(f"ap:rp:{action}:{repost_id}")
        assert parsed is not None
        assert (parsed.action, parsed.repost_id) == (action, repost_id)
    assert parse_repost_callback(f"ap:rp:stop:{repost_id}") is None
    assert parse_repost_callback(f"ap:bst:ok:{repost_id}") is None


def test_keyboard_has_four_buttons_under_64_bytes() -> None:
    keyboard = approval_keyboard(stored())
    datas = [b.callback_data for row in keyboard.rows for b in row]
    assert [d.split(":")[2] for d in datas] == ["ok", "orig", "cap", "no"]
    assert all(len(d.encode()) <= 64 for d in datas)


def test_approval_text_lists_original_metrics_reason_window_and_caption() -> None:
    repost = stored(window=window(), hook_text="Gancho forte")
    text = approval_text(
        ApprovalNotice(
            repost=repost,
            metrics=InsightMetrics(views=12345, reach=1000, likes=10),
            preview_link="https://x/r/1/preview.mp4",
        )
    )
    for part in (
        repost.permalink or "",
        "12.345",
        "Gancho forte",
        repost.reason,
        "Janela",
        "Legenda:",
        "Prévia: https://x/r/1/preview.mp4",
        "Expira em 12 h.",
    ):
        assert part in text


def test_approval_text_without_optional_parts() -> None:
    text = approval_text(
        ApprovalNotice(
            repost=stored(hook_text=None, permalink=None), metrics=InsightMetrics()
        )
    )
    assert "Gancho" not in text and "Janela" not in text and "Prévia" not in text
    assert "—" in metrics_line(InsightMetrics())


def test_approved_text_now_or_later_and_cover() -> None:
    now_text = approved_text(
        stored(cover_choice="grok", approved_at=NOW, publish_at=NOW)
    )
    assert "agora" in now_text and "Grok" in now_text
    later = approved_text(
        stored(
            cover_choice="original",
            approved_at=NOW,
            publish_at=NOW + timedelta(hours=5),
        )
    )
    assert "agora" not in later and "original" in later
    assert "agora" in approved_text(stored())


# Scenario: Aprovar schedules the best slot in the window
def test_publish_time_inside_window() -> None:
    win = window(1, 30)
    at = publish_time(PublishTimeQuery(window=win, now=NOW, signals=ScheduleSignals()))
    assert win.earliest <= at <= win.latest


def test_publish_time_prefers_the_audience_peak() -> None:
    win = window(1, 30)
    query = RecommendQuery(now=NOW, pov=False, signals=ScheduleSignals())
    day = (NOW + timedelta(hours=24)).astimezone(schedule_zone()).date()
    candidates = [
        s.at for s in slots_on(query, day) if win.earliest <= s.at <= win.latest
    ]
    target = candidates[-1]
    signals = ScheduleSignals(
        audience={target.hour: 100_000, (target.hour + 1) % 24: 0}
    )
    at = publish_time(PublishTimeQuery(window=win, now=NOW, signals=signals))
    assert at == target


# Scenario: Aprovar without a window publishes now
def test_publish_time_without_window_or_past_window_is_now() -> None:
    assert (
        publish_time(PublishTimeQuery(window=None, now=NOW, signals=ScheduleSignals()))
        == NOW
    )
    past = window(-10, -1)
    assert (
        publish_time(PublishTimeQuery(window=past, now=NOW, signals=ScheduleSignals()))
        == NOW
    )


def test_publish_time_with_an_empty_window_is_now() -> None:
    at = NOW + timedelta(hours=2)
    empty = PublishWindow(earliest=at, latest=at)
    query = PublishTimeQuery(window=empty, now=NOW, signals=ScheduleSignals())
    assert publish_time(query) == NOW


def test_publish_time_narrow_window_without_slot_is_its_start() -> None:
    narrow = PublishWindow(
        earliest=NOW.replace(minute=5) + timedelta(hours=2),
        latest=NOW.replace(minute=10) + timedelta(hours=2),
    )
    at = publish_time(
        PublishTimeQuery(window=narrow, now=NOW, signals=ScheduleSignals())
    )
    assert at == narrow.earliest
