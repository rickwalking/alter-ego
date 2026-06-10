"""Unit tests for presentation review repair helpers.

Feature: Presentation Review Repair
"""

from __future__ import annotations

import asyncio

import pytest

from rag_backend.application.services.carousel.presentation_review_repair import (
    attempt_locale_repair,
    repair_localized_slides,
    repair_localized_slides_sync,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)


class TestAttemptLocaleRepair:
    """Scenario: Repair one locale payload."""

    @pytest.mark.asyncio
    async def test_no_violations_returns_none(self) -> None:
        """Given a valid payload, when repair is attempted, then None is returned."""
        from rag_backend.application.services.carousel.presentation_policy import (
            load_presentation_policy,
        )

        policy = load_presentation_policy(DEFAULT_PRESENTATION_POLICY_VERSION)
        payload = {"slide_type": "intro", "heading": "Valid Heading", "body": "Valid body"}
        result = await attempt_locale_repair(
            payload,
            locale=LANGUAGE_PT,
            policy=policy,
            slide_index=1,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_repair_strips_emoji(self) -> None:
        """Given a payload with emoji, when repair runs, then emoji is removed."""
        from rag_backend.application.services.carousel.presentation_policy import (
            load_presentation_policy,
        )

        policy = load_presentation_policy(DEFAULT_PRESENTATION_POLICY_VERSION)
        payload = {"slide_type": "intro", "heading": "Hook 😀", "body": "Subtitle"}
        result = await attempt_locale_repair(
            payload,
            locale=LANGUAGE_PT,
            policy=policy,
            slide_index=1,
        )
        assert result is not None
        assert "😀" not in str(result.get("heading"))

    @pytest.mark.asyncio
    async def test_repair_en_sentence_case(self) -> None:
        """Given an EN heading starting lowercase, when repair runs, then it is capitalized."""
        from rag_backend.application.services.carousel.presentation_policy import (
            load_presentation_policy,
        )

        policy = load_presentation_policy(DEFAULT_PRESENTATION_POLICY_VERSION)
        payload = {"slide_type": "intro", "heading": "lowercase heading", "body": "Body"}
        result = await attempt_locale_repair(
            payload,
            locale=LANGUAGE_EN,
            policy=policy,
            slide_index=1,
        )
        assert result is not None
        heading = str(result.get("heading"))
        assert heading[0].isupper()

    @pytest.mark.asyncio
    async def test_repair_fails_when_violations_remain(self) -> None:
        """Given a payload that cannot be fully repaired, when repair runs, then None is returned."""
        from rag_backend.application.services.carousel.presentation_policy import (
            load_presentation_policy,
        )

        policy = load_presentation_policy(DEFAULT_PRESENTATION_POLICY_VERSION)
        # Very long body that exceeds budget even after repair
        payload = {
            "slide_type": "intro",
            "heading": "A",
            "body": "x" * 500,
        }
        result = await attempt_locale_repair(
            payload,
            locale=LANGUAGE_PT,
            policy=policy,
            slide_index=1,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_repair_with_none_slide_index(self) -> None:
        """Given a payload with no slide_index, when repair runs, then it still works."""
        from rag_backend.application.services.carousel.presentation_policy import (
            load_presentation_policy,
        )

        policy = load_presentation_policy(DEFAULT_PRESENTATION_POLICY_VERSION)
        payload = {"slide_type": "intro", "heading": "Hook 😀", "body": "Subtitle"}
        result = await attempt_locale_repair(
            payload,
            locale=LANGUAGE_PT,
            policy=policy,
            slide_index=None,
        )
        assert result is not None
        assert "😀" not in str(result.get("heading"))


class TestRepairLocalizedSlides:
    """Scenario: Repair multiple localized slides."""

    @pytest.mark.asyncio
    async def test_repair_multiple_slides(self) -> None:
        """Given slides with violations in both PT and EN, when repair runs, then both are repaired."""
        localized = [
            {
                "slide_index": 1,
                "slide_type": "intro",
                "presentation_pt": {
                    "slide_type": "intro",
                    "heading": "Hook 😀",
                    "body": "Subtitle",
                },
                "presentation_en": {
                    "slide_type": "intro",
                    "heading": "hook en",
                    "body": "Subtitle",
                },
            }
        ]

        repaired = await repair_localized_slides(localized)

        assert "😀" not in str(repaired[0]["presentation_pt"]["heading"])
        en_heading = str(repaired[0]["presentation_en"]["heading"])
        assert en_heading[0].isupper()

    @pytest.mark.asyncio
    async def test_skip_missing_locale_payload(self) -> None:
        """Given a slide with only PT payload, when repair runs, then EN is skipped."""
        localized = [
            {
                "slide_index": 1,
                "slide_type": "intro",
                "presentation_pt": {
                    "slide_type": "intro",
                    "heading": "Hook 😀",
                    "body": "Subtitle",
                },
            }
        ]

        repaired = await repair_localized_slides(localized)

        assert "😀" not in str(repaired[0]["presentation_pt"]["heading"])
        assert "presentation_en" not in repaired[0]

    @pytest.mark.asyncio
    async def test_no_violations_slide_unchanged(self) -> None:
        """Given a valid slide, when repair runs, then it is returned unchanged."""
        localized = [
            {
                "slide_index": 1,
                "slide_type": "intro",
                "presentation_pt": {
                    "slide_type": "intro",
                    "heading": "Valid",
                    "body": "Body",
                },
                "presentation_en": {
                    "slide_type": "intro",
                    "heading": "Valid",
                    "body": "Body",
                },
            }
        ]

        repaired = await repair_localized_slides(localized)

        assert repaired[0]["presentation_pt"]["heading"] == "Valid"
        assert repaired[0]["presentation_en"]["heading"] == "Valid"

    @pytest.mark.asyncio
    async def test_repair_with_string_slide_index(self) -> None:
        """Given a slide_index that is a string, when repair runs, then it is treated as None."""
        localized = [
            {
                "slide_index": "not-an-int",
                "slide_type": "intro",
                "presentation_pt": {
                    "slide_type": "intro",
                    "heading": "Hook 😀",
                    "body": "Subtitle",
                },
            }
        ]

        repaired = await repair_localized_slides(localized)

        assert "😀" not in str(repaired[0]["presentation_pt"]["heading"])

    @pytest.mark.asyncio
    async def test_repair_with_custom_policy_version(self) -> None:
        """Given a custom policy_version, when repair runs, then it uses that policy."""
        localized = [
            {
                "slide_index": 1,
                "slide_type": "intro",
                "presentation_pt": {
                    "slide_type": "intro",
                    "heading": "Hook 😀",
                    "body": "Subtitle",
                },
            }
        ]

        repaired = await repair_localized_slides(
            localized,
            policy_version=DEFAULT_PRESENTATION_POLICY_VERSION,
        )

        assert "😀" not in str(repaired[0]["presentation_pt"]["heading"])


class TestRepairLocalizedSlidesSync:
    """Scenario: Sync wrapper for repair."""

    def test_sync_routes_through_bounded_repair(self) -> None:
        """Given a slide with emoji, when sync repair runs, then emoji is removed."""
        localized = [
            {
                "slide_index": 1,
                "slide_type": "intro",
                "presentation_pt": {
                    "slide_type": "intro",
                    "heading": "Hook 😀",
                    "body": "Subtitle",
                },
            }
        ]

        repaired = repair_localized_slides_sync(localized)

        assert "😀" not in str(repaired[0]["presentation_pt"]["heading"])

    def test_sync_outside_event_loop(self) -> None:
        """Given sync call outside event loop, when repair runs, then it works."""
        localized = [
            {
                "slide_index": 1,
                "slide_type": "intro",
                "presentation_pt": {
                    "slide_type": "intro",
                    "heading": "Hook 😀",
                    "body": "Subtitle",
                },
            }
        ]

        # Ensure no event loop is running
        try:
            loop = asyncio.get_running_loop()
            pytest.skip("Test requires no running event loop")
        except RuntimeError:
            pass

        repaired = repair_localized_slides_sync(localized)

        assert "😀" not in str(repaired[0]["presentation_pt"]["heading"])

    def test_sync_inside_event_loop(self) -> None:
        """Given sync call inside event loop, when repair runs, then it works."""
        localized = [
            {
                "slide_index": 1,
                "slide_type": "intro",
                "presentation_pt": {
                    "slide_type": "intro",
                    "heading": "Hook 😀",
                    "body": "Subtitle",
                },
            }
        ]

        async def _run() -> list[dict[str, object]]:
            return repair_localized_slides_sync(localized)

        loop = asyncio.new_event_loop()
        try:
            repaired = loop.run_until_complete(_run())
        finally:
            loop.close()

        assert "😀" not in str(repaired[0]["presentation_pt"]["heading"])

    def test_sync_no_violations(self) -> None:
        """Given a valid slide, when sync repair runs, then it is returned unchanged."""
        localized = [
            {
                "slide_index": 1,
                "slide_type": "intro",
                "presentation_pt": {
                    "slide_type": "intro",
                    "heading": "Valid",
                    "body": "Body",
                },
            }
        ]

        repaired = repair_localized_slides_sync(localized)

        assert repaired[0]["presentation_pt"]["heading"] == "Valid"


class TestRepairLocalizedSlidesSyncEdgeCases:
    """Scenario: Edge cases for sync repair."""

    def test_empty_list(self) -> None:
        """Given an empty list, when repair runs, then empty list is returned."""
        repaired = repair_localized_slides_sync([])
        assert repaired == []

    def test_multiple_slides(self) -> None:
        """Given multiple slides, when repair runs, then all are repaired."""
        localized = [
            {
                "slide_index": 1,
                "slide_type": "intro",
                "presentation_pt": {
                    "slide_type": "intro",
                    "heading": "Hook 😀",
                    "body": "Subtitle",
                },
            },
            {
                "slide_index": 2,
                "slide_type": "content",
                "presentation_pt": {
                    "slide_type": "content",
                    "heading": "Another 😀",
                    "body": "Body",
                },
            },
        ]

        repaired = repair_localized_slides_sync(localized)

        assert "😀" not in str(repaired[0]["presentation_pt"]["heading"])
        assert "😀" not in str(repaired[1]["presentation_pt"]["heading"])
