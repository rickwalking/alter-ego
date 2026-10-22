"""Typed readers for loosely typed workflow-state values.

Scenario: strings_of keeps stripped non-empty strings.
Scenario: strings_of ignores non-list values.
Scenario: mappings_at returns only the mapping items.
Scenario: mappings_at tolerates a missing state or a non-list value.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.state_values import (
    mappings_at,
    strings_of,
)


# Scenario: strings_of keeps stripped non-empty strings.
def test_strings_of_strips_and_drops_blanks_and_non_strings() -> None:
    assert strings_of([" a ", "", "  ", 3, "b"]) == ("a", "b")


# Scenario: strings_of ignores non-list values.
def test_strings_of_non_list_is_empty() -> None:
    assert strings_of("abc") == ()
    assert strings_of(None) == ()


# Scenario: mappings_at returns only the mapping items.
def test_mappings_at_keeps_only_mappings() -> None:
    state = {"outline": [{"a": 1}, "skip", {"b": 2}]}

    assert mappings_at(state, "outline") == [{"a": 1}, {"b": 2}]


# Scenario: mappings_at tolerates a missing state or a non-list value.
def test_mappings_at_missing_state_or_non_list_is_empty() -> None:
    assert mappings_at(None, "outline") == []
    assert mappings_at({"outline": "text"}, "outline") == []
    assert mappings_at({}, "outline") == []
