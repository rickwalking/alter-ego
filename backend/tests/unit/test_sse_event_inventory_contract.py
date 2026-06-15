"""Contract test freezing backend SSE event-name constants (AE-0076).

Feature: SSE event names are frozen during the migration
See tests/features/sse_event_inventory.feature

Asserts that the three backend constant modules match the committed
source-of-truth artifact ``docs/architecture/sse-event-inventory.json``
exactly. On any drift the test fails with a message naming the changed
constant, so a rename cannot land silently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

import pytest

from rag_backend.application.services.carousel import (
    editorial_workflow_sse_constants as editorial,
)
from rag_backend.domain.constants import chat_stream, workflow_events

# Repo root: backend/tests/unit/<this file> -> up 3 = backend/, up 4 = repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARTIFACT_PATH = _REPO_ROOT / "docs" / "architecture" / "sse-event-inventory.json"

_EDITORIAL_KEY = "application/services/carousel/editorial_workflow_sse_constants.py"
_CHAT_KEY = "domain/constants/chat_stream.py"
_WORKFLOW_KEY = "domain/constants/workflow_events.py"


class _ModuleEntry(TypedDict):
    layer: str
    constants: dict[str, str]


def _load_artifact() -> dict[str, _ModuleEntry]:
    """Load the backend section of the frozen inventory artifact."""
    raw: dict[str, object] = json.loads(_ARTIFACT_PATH.read_text(encoding="utf-8"))
    backend = raw["backend"]
    assert isinstance(backend, dict)
    return cast("dict[str, _ModuleEntry]", backend)


def _actual_values(
    module_key: str,
    expected: dict[str, str],
) -> dict[str, object]:
    """Resolve the live constant values for a module by attribute name."""
    module_map = {
        _EDITORIAL_KEY: editorial,
        _CHAT_KEY: chat_stream,
        _WORKFLOW_KEY: workflow_events,
    }
    module = module_map[module_key]
    return {name: getattr(module, name, None) for name in expected}


_BACKEND_SECTION = _load_artifact()
_MODULE_KEYS = [_EDITORIAL_KEY, _CHAT_KEY, _WORKFLOW_KEY]

# Names matching these per-module rules are event-name constants and therefore
# in scope for the freeze. Anything else in a module (payload-field names,
# interval/config constants, consumer-group names) is intentionally NOT frozen.
_STREAM_NAME = "STREAM_CONTENT_EVENTS"


def _is_frozen_event_name(module_key: str, name: str) -> bool:
    """True if ``name`` is an event-name constant the inventory must freeze."""
    if module_key in (_EDITORIAL_KEY, _CHAT_KEY):
        return name.startswith("SSE_EVENT_")
    return name.startswith("EVENT_TYPE_") or name == _STREAM_NAME


def _live_frozen_names(module_key: str) -> set[str]:
    """Collect live module attributes that are in-scope event-name constants."""
    module_map = {
        _EDITORIAL_KEY: editorial,
        _CHAT_KEY: chat_stream,
        _WORKFLOW_KEY: workflow_events,
    }
    module = module_map[module_key]
    return {
        name
        for name in dir(module)
        if _is_frozen_event_name(module_key, name)
        and isinstance(getattr(module, name), str)
    }


class TestSseEventInventoryContract:
    """Backend SSE/event constants are frozen against the inventory."""

    def test_artifact_lists_every_backend_module(self) -> None:
        """Scenario: Backend constant matches the frozen inventory.

        Given the frozen SSE event-name inventory
        Then it enumerates all three backend constant modules.
        """
        assert set(_BACKEND_SECTION.keys()) == set(_MODULE_KEYS)

    @pytest.mark.parametrize("module_key", _MODULE_KEYS)
    def test_backend_constants_match_inventory(self, module_key: str) -> None:
        """Scenario: Backend constant matches the frozen inventory.

        Given the frozen SSE event-name inventory
        When the backend contract test compares constants to the inventory
        Then every constant value matches exactly.

        Scenario: A renamed event is caught in CI
        Given a backend constant whose value differs from the inventory
        Then the test fails and names the mismatched constant.
        """
        expected = _BACKEND_SECTION[module_key]["constants"]
        actual = _actual_values(module_key, expected)

        mismatches = [
            f"{name}: inventory={value!r} actual={actual[name]!r}"
            for name, value in expected.items()
            if actual[name] != value
        ]
        assert not mismatches, (
            f"SSE event-name drift in {module_key} (frozen until Phase 8). "
            "Update docs/architecture/sse-event-inventory.{json,md} and the "
            "frontend maps in the same PR if this change is intentional. "
            f"Mismatched constants: {'; '.join(mismatches)}"
        )

    @pytest.mark.parametrize("module_key", _MODULE_KEYS)
    def test_no_extra_or_missing_constants(self, module_key: str) -> None:
        """Scenario: A renamed event is caught in CI.

        A constant added to or removed from the artifact without updating the
        module (or vice versa) must surface as a contract failure.
        """
        expected = _BACKEND_SECTION[module_key]["constants"]
        actual = _actual_values(module_key, expected)
        missing = [name for name, value in actual.items() if value is None]
        assert not missing, (
            f"Inventory lists constants not defined in {module_key}: "
            f"{', '.join(missing)}"
        )

    @pytest.mark.parametrize("module_key", _MODULE_KEYS)
    def test_no_unfrozen_event_constants(self, module_key: str) -> None:
        """Scenario: A new event added to a module is caught in CI.

        Reverse direction (module -> artifact): a new ``SSE_EVENT_*`` /
        ``EVENT_TYPE_*`` constant added to a module without updating the
        inventory must fail the freeze, not slip through silently.
        """
        frozen = set(_BACKEND_SECTION[module_key]["constants"].keys())
        live = _live_frozen_names(module_key)
        unfrozen = sorted(live - frozen)
        assert not unfrozen, (
            f"Event-name constants in {module_key} are not in the frozen "
            "inventory (add them to docs/architecture/sse-event-inventory.json "
            f"and .md, plus the frontend maps, in the same PR): {unfrozen}"
        )
