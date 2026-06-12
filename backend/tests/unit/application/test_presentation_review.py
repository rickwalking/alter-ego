"""Unit tests for presentation review state builders."""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.presentation_review import (
    _RESOLVERS,
    _resolve_from_localized_slides,
    _resolve_from_slide_drafts,
    _resolve_from_validation,
    build_presentation_review_updates,
    build_presentation_review_updates_async,
    has_blocking_presentation_validation,
    resolve_presentation_review_from_state,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_ICON_NAME_NOT_ALLOWLISTED,
)


@pytest.mark.unit
class TestPresentationReview:
    """Gherkin: Versioned carousel presentation contract."""

    def test_builds_localized_slides_and_validation_from_legacy_drafts(self) -> None:
        """WHEN slide drafts exist THEN localized_slides and validation are available."""
        updates = build_presentation_review_updates(
            [
                {
                    "slide_index": 1,
                    "slide_type": "intro",
                    "title": "Hook",
                    "draft_text": "Subtitle",
                }
            ],
            translations_en={
                1: {"heading": "Hook EN", "body": "Subtitle EN"},
            },
        )

        localized = updates["localized_slides"]
        assert isinstance(localized, list)
        assert len(localized) == 1
        assert localized[0]["presentation_pt"]["heading"] == "Hook"
        assert localized[0]["presentation_en"]["heading"] == "Hook EN"
        validation = updates["presentation_validation"]
        assert isinstance(validation, dict)
        assert validation["blocking"] is False

    def test_flags_blocking_violations_for_invalid_copy(self) -> None:
        """WHEN visible copy violates a blocking rule THEN approval is blocked."""
        updates = build_presentation_review_updates([
            {
                "slide_index": 3,
                "slide_type": "content",
                "title": "Key insight",
                "draft_text": "Detail",
                "features": [
                    {
                        "icon_name": "rocket-ship",
                        "title": "Audit",
                        "body": "Weekly",
                    }
                ],
            }
        ])
        validation = updates["presentation_validation"]
        assert validation["blocking"] is True
        codes = {item["code"] for item in validation["violations"]}
        assert VIOLATION_ICON_NAME_NOT_ALLOWLISTED in codes
        assert has_blocking_presentation_validation(updates) is True

    def test_resolves_review_fields_from_slide_drafts_when_missing(self) -> None:
        """WHEN workflow state lacks review fields THEN they are derived on read."""
        resolved = resolve_presentation_review_from_state({
            "slide_drafts": [
                {
                    "slide_index": 1,
                    "slide_type": "intro",
                    "title": "Hook",
                    "draft_text": "Subtitle",
                }
            ]
        })
        assert len(resolved["localized_slides"]) == 1
        assert "presentation_validation" in resolved


_INTRO_DRAFT = {
    "slide_index": 1,
    "slide_type": "intro",
    "title": "Hook",
    "draft_text": "Subtitle",
}


def _validation_dict(updates: dict[str, object]) -> dict[str, object]:
    """Return the presentation_validation dict from review updates."""
    validation = updates["presentation_validation"]
    assert isinstance(validation, dict)
    return validation


def _localized_list(updates: dict[str, object]) -> list[object]:
    """Return the localized_slides list from review updates."""
    localized = updates["localized_slides"]
    assert isinstance(localized, list)
    return localized


def _strip_validated_at(updates: dict[str, object]) -> dict[str, object]:
    """Drop the wall-clock validated_at timestamp for stable comparisons."""
    validation = dict(_validation_dict(updates))
    validation.pop("validated_at", None)
    return {**updates, "presentation_validation": validation}


@pytest.mark.unit
class TestResolverChain:
    """Gherkin Feature: Chain-of-Responsibility (individual resolvers + chain)."""

    def test_resolvers_registered_in_documented_order(self) -> None:
        """THEN the chain runs validation -> localized_slides -> slide_drafts."""
        assert [
            _resolve_from_validation,
            _resolve_from_localized_slides,
            _resolve_from_slide_drafts,
        ] == _RESOLVERS

    def test_validation_resolver_succeeds_first(self) -> None:
        """Scenario: validation resolver succeeds first.

        Given state with valid "presentation_validation" key
        When resolve_presentation_review_from_state is called
        Then the validation resolver returns the result (fast path).
        """
        validation = {"blocking": False, "violations": []}
        state = {
            "presentation_validation": validation,
            "localized_slides": [{"slide_index": 9}],
            "presentation_policy_version": "v1",
        }
        resolved = resolve_presentation_review_from_state(state)
        # Identity of the validation dict proves the fast path returned it
        # untouched, i.e. no later resolver re-validated the slides.
        assert resolved["presentation_validation"] is validation
        assert resolved["localized_slides"] == [{"slide_index": 9}]

    def test_validation_resolver_returns_none_without_validation_key(self) -> None:
        """THEN the first resolver abstains when no validation dict is present."""
        assert _resolve_from_validation({"localized_slides": []}) is None

    def test_localized_resolver_revalidates_existing_slides(self) -> None:
        """THEN tier 2 builds a fresh validation report from localized_slides."""
        result = _resolve_from_localized_slides({"localized_slides": []})
        assert result is not None
        assert "presentation_validation" in result

    def test_localized_resolver_abstains_without_list(self) -> None:
        """THEN tier 2 abstains when localized_slides is not a list."""
        assert _resolve_from_localized_slides({}) is None

    def test_slide_drafts_resolver_builds_from_legacy_drafts(self) -> None:
        """THEN tier 3 builds review updates from legacy slide_drafts."""
        result = _resolve_from_slide_drafts({"slide_drafts": [dict(_INTRO_DRAFT)]})
        assert result is not None
        assert len(_localized_list(result)) == 1

    def test_slide_drafts_resolver_abstains_without_list(self) -> None:
        """THEN tier 3 abstains when slide_drafts is not a list."""
        assert _resolve_from_slide_drafts({}) is None

    def test_all_resolvers_return_none_falls_back_to_empty_review(self) -> None:
        """Scenario: all resolvers return None.

        Given state with no presentation data
        When resolve_presentation_review_from_state is called
        Then an empty review (built from no drafts) is returned.
        """
        resolved = resolve_presentation_review_from_state({})
        assert _localized_list(resolved) == []
        assert _validation_dict(resolved)["blocking"] is False


@pytest.mark.unit
class TestAsyncSyncParity:
    """Gherkin Feature: Async/Sync Parity (shared _build_presentation_review_common)."""

    @pytest.mark.asyncio
    async def test_sync_and_async_produce_same_output(self) -> None:
        """Scenario: sync and async produce same output.

        Given identical inputs for sync and async variants
        When both functions complete
        Then their outputs are identical.
        """
        drafts = [dict(_INTRO_DRAFT)]
        translations: dict[int, dict[str, object]] = {
            1: {"heading": "Hook EN", "body": "Subtitle EN"}
        }
        sync_result = build_presentation_review_updates(
            [dict(_INTRO_DRAFT)], translations_en=translations
        )
        async_result = await build_presentation_review_updates_async(
            drafts, translations_en=translations
        )
        # validated_at timestamps differ by wall clock; compare everything else.
        assert _strip_validated_at(sync_result) == _strip_validated_at(async_result)

    @pytest.mark.asyncio
    async def test_empty_drafts_parity_for_empty_review(self) -> None:
        """THEN both variants return the same empty-review shape for no drafts."""
        sync_result = build_presentation_review_updates([])
        async_result = await build_presentation_review_updates_async([])
        assert _strip_validated_at(sync_result) == _strip_validated_at(async_result)
