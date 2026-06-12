"""Unit tests for editorial workflow response field extractors (AE-0044).

Covers the Field Descriptor Mapping pattern in
``editorial_workflow_routes_response``: each pure extractor, the
``_FIELD_MAPPING`` constant, the public builder, and the deprecated alias.

Gherkin scenarios (see ticket AE-0044 "Field Descriptor Mapping"):
  - build_workflow_state_response with full state
  - build_workflow_state_response with empty state
  - deprecated wrapper
"""

from __future__ import annotations

import warnings

import pytest

from rag_backend.api.routes.carousels.editorial_workflow_routes_response import (
    _FIELD_MAPPING,
    _bool_field,
    _dict_field,
    _error_message_field,
    _int_field,
    _int_map_field,
    _list_field,
    _localized_reviews_field,
    _policy_version_field,
    _status_field,
    _string_field,
    _string_list_map_field,
    _validation_field,
    build_editorial_workflow_state_response,
    build_workflow_state_response,
)
from rag_backend.api.schemas.carousel_workflow import (
    LocalizedSlideReview,
    SlideValidationReportResponse,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel_workflow import (
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_WORKFLOW_PHASE_FAILED,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_DEFAULT_STATUS,
    STATE_FIELD_PHASE_PROGRESS,
    STATE_FIELD_PROJECT_ID,
    STATE_FIELD_STATUS,
)

_KEY = "field"


# ── _string_field ───────────────────────────────────────────────────────────


class TestStringField:
    """Scenario: empty state -> string fields default to ''."""

    def test_missing_key_returns_empty(self) -> None:
        assert _string_field(_KEY)({}) == ""

    def test_none_value_returns_empty(self) -> None:
        assert _string_field(_KEY)({_KEY: None}) == ""

    def test_string_value_returned(self) -> None:
        assert _string_field(_KEY)({_KEY: "hello"}) == "hello"

    def test_non_string_coerced(self) -> None:
        assert _string_field(_KEY)({_KEY: 42}) == "42"


# ── _list_field ─────────────────────────────────────────────────────────────


class TestListField:
    """Scenario: empty state -> list fields default to []."""

    def test_missing_key_returns_empty_list(self) -> None:
        assert _list_field(_KEY)({}) == []

    def test_none_value_returns_empty_list(self) -> None:
        assert _list_field(_KEY)({_KEY: None}) == []

    def test_non_list_value_returns_empty_list(self) -> None:
        assert _list_field(_KEY)({_KEY: "notalist"}) == []

    def test_list_value_is_copied(self) -> None:
        source = [1, 2, 3]
        result = _list_field(_KEY)({_KEY: source})
        assert result == [1, 2, 3]
        assert result is not source


# ── _int_field ──────────────────────────────────────────────────────────────


class TestIntField:
    """Mutation-killing coverage for integer coercion branches."""

    def test_missing_key_returns_zero(self) -> None:
        assert _int_field(_KEY)({}) == 0

    def test_int_value_returned(self) -> None:
        assert _int_field(_KEY)({_KEY: 7}) == 7

    def test_numeric_string_coerced(self) -> None:
        assert _int_field(_KEY)({_KEY: "12"}) == 12

    def test_negative_numeric_string_coerced(self) -> None:
        assert _int_field(_KEY)({_KEY: "-3"}) == -3

    def test_blank_string_returns_zero(self) -> None:
        assert _int_field(_KEY)({_KEY: "   "}) == 0

    def test_non_numeric_string_returns_zero(self) -> None:
        assert _int_field(_KEY)({_KEY: "abc"}) == 0

    def test_float_value_returns_zero(self) -> None:
        assert _int_field(_KEY)({_KEY: 1.5}) == 0


# ── _bool_field ─────────────────────────────────────────────────────────────


class TestBoolField:
    def test_missing_key_is_false(self) -> None:
        assert _bool_field(_KEY)({}) is False

    def test_truthy_value(self) -> None:
        assert _bool_field(_KEY)({_KEY: True}) is True

    def test_falsey_value(self) -> None:
        assert _bool_field(_KEY)({_KEY: 0}) is False


# ── _dict_field ─────────────────────────────────────────────────────────────


class TestDictField:
    def test_missing_key_returns_empty_dict(self) -> None:
        assert _dict_field(_KEY)({}) == {}

    def test_non_dict_returns_empty_dict(self) -> None:
        assert _dict_field(_KEY)({_KEY: [1]}) == {}

    def test_dict_value_is_copied(self) -> None:
        source = {"a": 1}
        result = _dict_field(_KEY)({_KEY: source})
        assert result == {"a": 1}
        assert result is not source


# ── _string_list_map_field ──────────────────────────────────────────────────


class TestStringListMapField:
    def test_missing_key_returns_empty(self) -> None:
        assert _string_list_map_field(_KEY)({}) == {}

    def test_non_dict_returns_empty(self) -> None:
        assert _string_list_map_field(_KEY)({_KEY: "x"}) == {}

    def test_only_list_values_kept_and_stringified(self) -> None:
        raw = {"a": [1, "two"], "b": "skip", "c": [3]}
        assert _string_list_map_field(_KEY)({_KEY: raw}) == {
            "a": ["1", "two"],
            "c": ["3"],
        }


# ── _int_map_field ──────────────────────────────────────────────────────────


class TestIntMapField:
    def test_missing_key_returns_empty(self) -> None:
        assert _int_map_field(_KEY)({}) == {}

    def test_non_dict_returns_empty(self) -> None:
        assert _int_map_field(_KEY)({_KEY: 5}) == {}

    def test_int_and_digit_strings_kept(self) -> None:
        raw = {"a": 2, "b": "3", "c": "x", "d": 1.0}
        assert _int_map_field(_KEY)({_KEY: raw}) == {"a": 2, "b": 3}


# ── _localized_reviews_field ────────────────────────────────────────────────


class TestLocalizedReviewsField:
    def test_missing_key_returns_empty(self) -> None:
        assert _localized_reviews_field(_KEY)({}) == []

    def test_non_list_returns_empty(self) -> None:
        assert _localized_reviews_field(_KEY)({_KEY: {}}) == []

    def test_valid_entry_mapped(self) -> None:
        raw = [
            {
                "slide_index": 0,
                "slide_type": "intro",
                "presentation_pt": {"heading": "ola"},
                "presentation_en": {"heading": "hi"},
            },
            "ignored",
            {"slide_index": "no", "slide_type": "x"},
        ]
        result = _localized_reviews_field(_KEY)({_KEY: raw})
        assert len(result) == 1
        review = result[0]
        assert isinstance(review, LocalizedSlideReview)
        assert review.slide_index == 0
        assert review.slide_type == "intro"
        assert review.presentation_pt == {"heading": "ola"}
        assert review.presentation_en == {"heading": "hi"}

    def test_non_dict_presentation_defaults_empty(self) -> None:
        raw = [{"slide_index": 1, "slide_type": "body", "presentation_pt": "bad"}]
        result = _localized_reviews_field(_KEY)({_KEY: raw})
        assert result[0].presentation_pt == {}
        assert result[0].presentation_en == {}


# ── _validation_field ───────────────────────────────────────────────────────


class TestValidationField:
    def test_missing_key_returns_none(self) -> None:
        assert _validation_field(_KEY)({}) is None

    def test_non_dict_returns_none(self) -> None:
        assert _validation_field(_KEY)({_KEY: []}) is None

    def test_incomplete_report_returns_none(self) -> None:
        raw = {"validation_status": "ok", "blocking": True}  # missing validated_at
        assert _validation_field(_KEY)({_KEY: raw}) is None

    def test_non_bool_blocking_returns_none(self) -> None:
        raw = {"validation_status": "ok", "validated_at": "t", "blocking": "yes"}
        assert _validation_field(_KEY)({_KEY: raw}) is None

    def test_valid_report_with_violations(self) -> None:
        raw = {
            "validation_status": "invalid",
            "validated_at": "2026-01-01",
            "blocking": True,
            "violations": [
                {
                    "code": "c1",
                    "message": "m1",
                    "slide_index": 2,
                    "locale": "pt",
                    "field": "heading",
                },
                "ignored",
                {"code": "c2"},  # missing message -> skipped
            ],
        }
        report = _validation_field(_KEY)({_KEY: raw})
        assert isinstance(report, SlideValidationReportResponse)
        assert report.validation_status == "invalid"
        assert report.validated_at == "2026-01-01"
        assert report.blocking is True
        assert len(report.violations) == 1
        violation = report.violations[0]
        assert violation.code == "c1"
        assert violation.slide_index == 2
        assert violation.locale == "pt"
        assert violation.field == "heading"

    def test_violation_optional_fields_wrong_type_become_none(self) -> None:
        raw = {
            "validation_status": "invalid",
            "validated_at": "t",
            "blocking": False,
            "violations": [
                {
                    "code": "c",
                    "message": "m",
                    "slide_index": "x",
                    "locale": 1,
                    "field": 2,
                }
            ],
        }
        report = _validation_field(_KEY)({_KEY: raw})
        assert report is not None
        violation = report.violations[0]
        assert violation.slide_index is None
        assert violation.locale is None
        assert violation.field is None


# ── _status_field / _policy_version_field ────────────────────────────────────


class TestStatusAndPolicyFields:
    def test_status_defaults_to_draft(self) -> None:
        assert _status_field({}) == STATE_DEFAULT_STATUS

    def test_status_value_returned(self) -> None:
        assert _status_field({STATE_FIELD_STATUS: "published"}) == "published"

    def test_policy_version_none_when_absent(self) -> None:
        assert _policy_version_field({}) is None

    def test_policy_version_stringified(self) -> None:
        assert _policy_version_field({"presentation_policy_version": 2}) == "2"


# ── _error_message_field (AE-0009) ───────────────────────────────────────────


class TestErrorMessageField:
    """AE-0009 backend: error_message included when present, omitted when absent.

    Feature: Workflow Error Feedback & Retry
    Scenario: Error message persists across page refresh
      Given the editorial workflow has phase_status "failed"
      And error_message is stored in the workflow state
      When the user refreshes the page
      Then the error card is still displayed
      And the error message matches the stored error_message

    QA F-1 (AE-0009): error_message MUST be the SAME client-safe string the SSE
    path emits. Raw persisted ``workflow_error`` values that are not on the
    ``CLIENT_SAFE_SSE_ERROR_MESSAGES`` allowlist must collapse to the generic
    phase-failed message (no raw internal error / traceback / secret leakage).
    """

    def test_missing_returns_none(self) -> None:
        assert _error_message_field({}) is None

    def test_blank_workflow_error_returns_none(self) -> None:
        assert _error_message_field({"workflow_error": ""}) is None

    def test_allowlisted_error_passes_through(self) -> None:
        # ERR_INVALID_JSON is on the SSE client-safe allowlist.
        assert (
            _error_message_field({"workflow_error": ERR_INVALID_JSON})
            == ERR_INVALID_JSON
        )

    def test_non_allowlisted_raw_error_mapped_to_safe_message(self) -> None:
        # F-1: a raw internal error (with secrets/traceback) must NOT leak;
        # it collapses to the generic client-safe phase-failed message.
        raw_internal = (
            "Traceback: psycopg2.OperationalError password=hunter2 at db.py:42"
        )
        result = _error_message_field({"workflow_error": raw_internal})
        assert result == ERR_WORKFLOW_PHASE_FAILED
        assert "hunter2" not in (result or "")

    def test_error_message_fallback_key_mapped_to_safe_message(self) -> None:
        # Fallback key honored for presence, but still sanitized.
        assert _error_message_field({"error_message": "boom"}) == (
            ERR_WORKFLOW_PHASE_FAILED
        )

    def test_workflow_error_preferred_over_error_message(self) -> None:
        # Allowlisted primary passes through over a (different) fallback.
        state = {
            "workflow_error": ERR_PERSONA_SCORE_TOO_LOW,
            "error_message": ERR_INVALID_JSON,
        }
        assert _error_message_field(state) == ERR_PERSONA_SCORE_TOO_LOW

    def test_non_string_mapped_to_safe_message(self) -> None:
        # Non-string raw error is present but not allowlisted -> safe message.
        assert _error_message_field({"workflow_error": 500}) == (
            ERR_WORKFLOW_PHASE_FAILED
        )


# ── _FIELD_MAPPING ──────────────────────────────────────────────────────────


class TestFieldMapping:
    """AC: _FIELD_MAPPING defined as module-level constant with 12+ entries."""

    def test_has_at_least_twelve_entries(self) -> None:
        assert len(_FIELD_MAPPING) >= 12

    def test_entries_are_name_extractor_pairs(self) -> None:
        for name, extractor in _FIELD_MAPPING:
            assert isinstance(name, str)
            assert callable(extractor)

    def test_field_names_are_unique(self) -> None:
        names = [name for name, _ in _FIELD_MAPPING]
        assert len(names) == len(set(names))


# ── build_editorial_workflow_state_response ─────────────────────────────────


class TestBuilder:
    """Scenarios: full state, empty state."""

    def test_empty_state_uses_defaults(self) -> None:
        # Scenario: empty state -> strings '', lists [], optionals None.
        response = build_editorial_workflow_state_response({})
        assert response.project_id == ""
        assert response.research_findings == []
        assert response.phase_progress is None
        assert response.status == STATE_DEFAULT_STATUS
        assert response.lock_version == 1
        assert response.localized_slides == []
        assert response.presentation_validation is None

    def test_full_state_maps_fields(self) -> None:
        # Scenario: full state -> all fields match input values.
        state = {
            STATE_FIELD_PROJECT_ID: "proj-1",
            "current_phase": "research",
            "design_applied": True,
            "phase_feedback": {"research": ["ok"]},
            "revision_count": {"research": "4"},
        }
        response = build_editorial_workflow_state_response(state)
        assert response.project_id == "proj-1"
        assert response.current_phase == "research"
        assert response.design_applied is True
        assert response.phase_feedback == {"research": ["ok"]}
        assert response.revision_count == {"research": 4}

    def test_explicit_phase_progress_override(self) -> None:
        state = {STATE_FIELD_PHASE_PROGRESS: {"from": "state"}}
        response = build_editorial_workflow_state_response(
            state, phase_progress={"from": "arg"}, lock_version=9
        )
        assert response.phase_progress == {"from": "arg"}
        assert response.lock_version == 9

    def test_phase_progress_falls_back_to_state(self) -> None:
        state = {STATE_FIELD_PHASE_PROGRESS: {"from": "state"}}
        response = build_editorial_workflow_state_response(state)
        assert response.phase_progress == {"from": "state"}

    def test_non_dict_phase_progress_becomes_none(self) -> None:
        state = {STATE_FIELD_PHASE_PROGRESS: "notadict"}
        response = build_editorial_workflow_state_response(state)
        assert response.phase_progress is None

    def test_error_message_omitted_when_absent(self) -> None:
        # AE-0009: error_message is None on healthy (non-failed) states.
        response = build_editorial_workflow_state_response({})
        assert response.error_message is None

    def test_error_message_surfaced_from_workflow_error(self) -> None:
        # AE-0009 Scenario: Error message persists across page refresh.
        state = {
            STATE_FIELD_PROJECT_ID: "p",
            "phase_status": "failed",
            "workflow_error": "Invalid JSON response from LLM",
        }
        response = build_editorial_workflow_state_response(state)
        assert response.error_message == "Invalid JSON response from LLM"


# ── deprecated wrapper ──────────────────────────────────────────────────────


class TestDeprecatedWrapper:
    """Scenario: deprecated wrapper -> a DeprecationWarning is issued."""

    def test_emits_deprecation_warning(self) -> None:
        with pytest.warns(DeprecationWarning):
            build_workflow_state_response({})

    def test_returns_same_result_as_new_function(self) -> None:
        state = {STATE_FIELD_PROJECT_ID: "p", "current_phase": "design"}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            old = build_workflow_state_response(dict(state), lock_version=3)
        new = build_editorial_workflow_state_response(dict(state), lock_version=3)
        assert old.model_dump() == new.model_dump()
