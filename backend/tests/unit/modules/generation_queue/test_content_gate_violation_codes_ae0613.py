"""The content gate event names the rules that fired, as known rule ids only.

Feature: content_gate_violation_codes_ae0613.feature
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

import rag_backend
from rag_backend.domain.constants.violation_codes import KNOWN_VIOLATION_CODES
from rag_backend.modules.generation_queue.application.content_gate_codes import (
    violation_code_details,
)
from rag_backend.modules.generation_queue.application.generation_events import (
    generation_event_scope,
)
from rag_backend.modules.generation_queue.constants import (
    DETAIL_TRUNCATED,
    VIOLATION_CODES_MAX_CHARS,
    VIOLATION_CODES_SEPARATOR,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEventInput,
    GenerationEventRun,
    sanitize_event_details,
)
from rag_backend.modules.generation_queue.domain.models import GenerationKind
from rag_backend.modules.generation_queue.events_public import record_phase_artifacts

_CONTRACTS = (
    Path(rag_backend.__file__).parent / "agents/skills/carousel-pipeline/contracts"
)
_TRUNCATED = "truncated"
_CODES = "violation_codes"
_PLANTED = "private slide text"
_RULE_ID = re.compile(r"[a-z0-9_]+")


@dataclass
class _Recorder:
    events: list[GenerationEventInput] = field(default_factory=list)

    async def record(
        self, run: GenerationEventRun, event: GenerationEventInput
    ) -> bool:
        self.events.append(event)
        return True


def _blocker(code: object) -> dict[str, object]:
    return {
        "code": code,
        "message": _PLANTED,
        "field": _PLANTED,
        "severity": "blocker",
    }


def _warning(code: str) -> dict[str, object]:
    return {"code": code, "message": _PLANTED, "severity": "warning"}


def _is_storable_rule_id(code: str) -> bool:
    return (
        _RULE_ID.fullmatch(code) is not None
        and sanitize_event_details({_CODES: code}) == {_CODES: code}
    )


def _report(violations: list[object]) -> dict[str, object]:
    return {
        "validation_status": "invalid",
        "blocking": True,
        "violations": violations,
    }


async def _gate_details(validation: Mapping[str, object]) -> Mapping[str, object]:
    recorder = _Recorder()
    run = GenerationEventRun(
        id=uuid4(), kind=GenerationKind.WORKFLOW_RESUME, carousel_project_id="p1"
    )
    async with generation_event_scope(run, recorder):
        await record_phase_artifacts(
            "content", {"content_gate_validation": validation}, None
        )
    gate = next(e for e in recorder.events if e.event_type == "content_gate")
    return gate.details


async def test_blocked_gate_stores_distinct_sorted_codes() -> None:
    """Scenario: A blocked gate stores the codes of the rules that fired"""
    details = await _gate_details(
        _report([
            _blocker("heading_not_sentence_case_en"),
            _blocker("body_too_long"),
            _blocker("heading_not_sentence_case_en"),
        ])
    )

    assert details == {
        "violation_count": 3,
        "blocking_count": 1,
        _CODES: "body_too_long.heading_not_sentence_case_en",
    }


async def test_passing_gate_stores_no_codes() -> None:
    """Scenario: A passing gate stores no codes"""
    details = await _gate_details({})

    assert details == {"violation_count": 0, "blocking_count": 0}
    assert sanitize_event_details(dict(details)) == details


async def test_violation_text_never_reaches_the_details() -> None:
    """Scenario: A violation with a message and slide text stores the code only"""
    details = await _gate_details(_report([_blocker("copy_truncated")]))

    assert details[_CODES] == "copy_truncated"
    assert _PLANTED not in str(details)


@pytest.mark.parametrize(
    "unknown",
    ["not_a_rule", _PLANTED, "heading_too_long.body_too_long", "HEADING_EMPTY", ""],
)
async def test_unknown_code_is_dropped_and_marked(unknown: str) -> None:
    """Scenario: An unknown or free-text code is dropped"""
    details = await _gate_details(_report([_blocker("markup_leak"), _blocker(unknown)]))

    assert details[_CODES] == "markup_leak"
    assert details[_TRUNCATED] is True


@pytest.mark.parametrize(
    "entry",
    [
        "markup_leak",
        None,
        {"message": _PLANTED},
        {"code": 7},
        {"code": ["markup_leak"]},
        {"code": {"nested": _PLANTED}},
    ],
)
async def test_malformed_entry_is_dropped_without_failing(entry: object) -> None:
    """Scenario: A malformed violation entry never breaks the event"""
    details = await _gate_details(_report([entry]))

    assert _CODES not in details
    assert details[_TRUNCATED] is True
    assert _PLANTED not in str(details)


def test_a_blocking_list_contributes_its_codes() -> None:
    """Scenario: A blocked gate stores the codes of the rules that fired"""
    details = violation_code_details({
        "blocking": [{"code": "copy_truncated"}],
        "violations": [{"code": "copy_truncated", "severity": "warning"}],
    })

    assert details == {_CODES: "copy_truncated"}


def test_every_rule_firing_stays_within_the_sanitizer_bounds() -> None:
    """Scenario: Many codes stay within the sanitizer bounds"""
    fired = [_blocker(code) for code in sorted(KNOWN_VIOLATION_CODES)]

    details = violation_code_details(_report(list(fired)))
    value = details[_CODES]

    assert isinstance(value, str)
    assert len(value) <= VIOLATION_CODES_MAX_CHARS
    assert details[_TRUNCATED] is True
    assert sanitize_event_details({_CODES: value}) == {_CODES: value}
    kept = value.split(VIOLATION_CODES_SEPARATOR)
    assert kept == sorted(set(kept))
    assert set(kept) <= KNOWN_VIOLATION_CODES


def test_a_longest_pair_of_codes_fits_and_nothing_is_marked() -> None:
    """Scenario: Many codes stay within the sanitizer bounds"""
    longest = sorted(KNOWN_VIOLATION_CODES, key=len)[-2:]

    details = violation_code_details(_report([_blocker(c) for c in longest]))

    assert details == {_CODES: VIOLATION_CODES_SEPARATOR.join(sorted(longest))}


def test_a_shorter_code_fills_the_room_a_long_one_cannot_use() -> None:
    """Scenario: Many codes stay within the sanitizer bounds"""
    fired = [
        "body_too_long",
        "heading_not_sentence_case_en",
        "layout_presentation_below_footer",
        "markup_leak",
    ]

    details = violation_code_details(_report([_blocker(c) for c in fired]))

    assert details == {
        _CODES: "body_too_long.heading_not_sentence_case_en.markup_leak",
        _TRUNCATED: True,
    }


async def test_blocker_survives_warnings_that_sort_first() -> None:
    """Scenario: Blockers are kept ahead of warnings when space runs out"""
    warnings: list[object] = [
        _warning(code)
        for code in sorted(KNOWN_VIOLATION_CODES)
        if code != "wrong_language"
    ]
    details = await _gate_details(_report([*warnings, _blocker("wrong_language")]))

    assert "wrong_language" in str(details[_CODES]).split(VIOLATION_CODES_SEPARATOR)
    assert details[_TRUNCATED] is True


def test_a_code_seen_as_warning_and_blocker_counts_as_a_blocker() -> None:
    """Scenario: Blockers are kept ahead of warnings when space runs out"""
    warnings: list[object] = [
        _warning(code)
        for code in sorted(KNOWN_VIOLATION_CODES)
        if code != "wrong_language"
    ]

    details = violation_code_details(
        _report([
            _warning("wrong_language"),
            *warnings,
            _blocker("wrong_language"),
        ])
    )

    assert "wrong_language" in str(details[_CODES])


def test_a_warning_never_replaces_a_blocker_that_did_not_fit() -> None:
    """Scenario: A warning never takes the place of a dropped blocker"""
    details = violation_code_details(
        _report([
            _blocker("body_too_long"),
            _blocker("heading_not_sentence_case_en"),
            _blocker("layout_presentation_below_footer"),
            _warning("markup_leak"),
        ])
    )

    assert details == {
        _CODES: "body_too_long.heading_not_sentence_case_en",
        _TRUNCATED: True,
    }


@pytest.mark.parametrize(
    "lost",
    [_blocker("not_a_rule"), {"message": _PLANTED}, {"code": 7}, "markup_leak"],
)
def test_a_warning_is_not_stored_when_a_blocker_was_dropped_as_unknown(
    lost: object,
) -> None:
    """Scenario: A warning never takes the place of a dropped blocker"""
    details = violation_code_details(
        _report([lost, _blocker("body_too_long"), _warning("markup_leak")])
    )

    assert details == {_CODES: "body_too_long", _TRUNCATED: True}


def test_a_warning_stays_when_only_a_warning_was_dropped() -> None:
    """Scenario: A warning never takes the place of a dropped blocker"""
    unknown_warning = {"code": "not_a_rule", "severity": "warning"}

    details = violation_code_details(
        _report([unknown_warning, _blocker("body_too_long"), _warning("markup_leak")])
    )

    assert details == {_CODES: "body_too_long.markup_leak", _TRUNCATED: True}


def test_warnings_fill_the_room_once_every_blocker_fits() -> None:
    """Scenario: A warning never takes the place of a dropped blocker"""
    details = violation_code_details(
        _report([
            _blocker("body_too_long"),
            _blocker("heading_not_sentence_case_en"),
            _warning("layout_presentation_below_footer"),
            _warning("markup_leak"),
        ])
    )

    assert details == {
        _CODES: "body_too_long.heading_not_sentence_case_en.markup_leak",
        _TRUNCATED: True,
    }


def test_the_sanitizer_still_drops_a_key_that_is_not_allowlisted() -> None:
    """Scenario: The sanitizer still bites around the new key"""
    details = sanitize_event_details({
        _CODES: "markup_leak",
        "violation_messages": "markup_leak",
        "violation_code": "markup_leak",
    })

    assert details == {_CODES: "markup_leak", _TRUNCATED: True}


@pytest.mark.parametrize(
    "value",
    [
        "a" * (VIOLATION_CODES_MAX_CHARS + 1),
        "a" * 121,
        "",
        _PLANTED,
        "markup_leak,body_empty",
        "markup_leak body_empty",
        'markup_leak"',
        ["markup_leak"],
        {"markup_leak": 1},
    ],
)
def test_the_sanitizer_rejects_a_bad_value_under_the_new_key(value: object) -> None:
    """Scenario: The sanitizer still bites around the new key"""
    assert sanitize_event_details({_CODES: value}) == {_TRUNCATED: True}


def test_the_truncated_detail_is_the_key_the_sanitizer_writes() -> None:
    """Scenario: The sanitizer still bites around the new key

    The sanitizer has no constant to import, so this ties the two literals together.
    """
    assert sanitize_event_details({"not_allowlisted": 1}) == {DETAIL_TRUNCATED: True}
    assert sanitize_event_details({DETAIL_TRUNCATED: True}) == {DETAIL_TRUNCATED: True}


def test_the_length_budget_is_the_sanitizer_limit() -> None:
    """Scenario: Many codes stay within the sanitizer bounds"""
    fits = "a" * VIOLATION_CODES_MAX_CHARS

    assert sanitize_event_details({_CODES: fits}) == {_CODES: fits}


def test_known_codes_cover_every_contract_rule() -> None:
    """Scenario: An unknown or free-text code is dropped

    A rule added to a contract without a constant would otherwise vanish.
    """
    rules: set[str] = set()
    for path in _CONTRACTS.glob("*.yaml"):
        rules |= set(yaml.safe_load(path.read_text()).get("rule_severities", {}))

    assert rules
    assert rules <= KNOWN_VIOLATION_CODES


def test_known_codes_are_bare_rule_ids_without_the_separator() -> None:
    """Scenario: A blocked gate stores the codes of the rules that fired"""
    assert "heading_not_sentence_case_en" in KNOWN_VIOLATION_CODES
    assert "hook_word_limit" in KNOWN_VIOLATION_CODES
    assert all(code.islower() for code in KNOWN_VIOLATION_CODES)
    assert not any(VIOLATION_CODES_SEPARATOR in c for c in KNOWN_VIOLATION_CODES)
    assert max(map(len, KNOWN_VIOLATION_CODES)) <= VIOLATION_CODES_MAX_CHARS


def test_every_known_code_is_a_rule_id_the_sanitizer_stores() -> None:
    """Scenario: Every known code is a value the sanitizer stores"""
    rejected = [c for c in KNOWN_VIOLATION_CODES if not _is_storable_rule_id(c)]

    assert KNOWN_VIOLATION_CODES
    assert rejected == []


@pytest.mark.parametrize(
    "not_a_code",
    ["Not a rule id.", "UPPER_CASE", "dotted.code", "trailing_newline\n", "a" * 65, ""],
)
def test_the_rule_id_check_fires_on_a_value_that_is_not_a_code(
    not_a_code: str,
) -> None:
    """Scenario: Every known code is a value the sanitizer stores"""
    assert not _is_storable_rule_id(not_a_code)
