"""AE-0268: carousel theme is a string reference, not the CarouselTheme enum.

Feature: Carousel theme stored as a string reference (no behaviour change)
(.agent/tasks/AE-0268-carousel-theme-as-string-reference-prod-census-gate.md)

The DB column was already ``String(30)`` (not a PG enum), so this is a
domain-layer type change with no DDL: ``CarouselProject.theme`` is now a plain
``str`` (root key | "auto" | future custom UUID). The enum survives only as the
canonical root-key list. These tests pin that resolution is unchanged.
"""

from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.theme_resolver import resolve_theme
from rag_backend.domain.constants import CAROUSEL_THEMES
from rag_backend.domain.models import CarouselProject, CarouselTheme
from rag_backend.domain.models.carousel import validate_theme_reference


def _project(theme: str) -> CarouselProject:
    return CarouselProject(topic="t", audience="a", niche="n", theme=theme)


@pytest.mark.unit
class TestCarouselThemeStringReference:
    def test_theme_defaults_to_auto_string(self) -> None:
        project = CarouselProject(topic="t", audience="a", niche="n")
        assert project.theme == "auto"
        assert isinstance(project.theme, str)

    def test_explicit_root_key_resolves_to_its_palette(self) -> None:
        # Scenario: an explicit root-key theme resolves to its palette.
        project = _project("plasma_magenta")
        assert resolve_theme(project) == CAROUSEL_THEMES["plasma_magenta"]

    def test_plain_string_theme_round_trips(self) -> None:
        # Scenario: existing enum-valued projects round-trip as plain strings.
        for key in ("cybersecurity", "paper_editorial", CarouselTheme.AUTO.value):
            assert _project(key).theme == key

    def test_auto_string_takes_the_detection_path(self) -> None:
        # "auto" must NOT short-circuit to the explicit-key branch.
        resolved = resolve_theme(_project("auto"))
        assert set(resolved) == {"primary", "accent", "background"}

    def test_unknown_key_falls_back_to_first_category(self) -> None:
        # An explicit but unknown key degrades to the first category palette
        # (unchanged guard behaviour), never raising.
        resolved = resolve_theme(_project("not_a_real_theme"))
        assert set(resolved) == {"primary", "accent", "background"}

    def test_snapshot_short_circuits_resolution(self) -> None:
        # AE-0269 D9: a project carrying a theme_snapshot renders from it,
        # bypassing live resolution — so palette edits never change past work.
        project = CarouselProject(
            topic="t",
            audience="a",
            niche="n",
            theme="auto",
            theme_snapshot={
                "primary": "#aaaaaa",
                "accent": "#bbbbbb",
                "background": "#cccccc",
                "mode": "dark",
                "resolved_ref": "some-custom-id",
                "resolved_at": "2026-06-23T00:00:00",
            },
        )
        assert resolve_theme(project) == {
            "primary": "#aaaaaa",
            "accent": "#bbbbbb",
            "background": "#cccccc",
        }


@pytest.mark.unit
class TestValidateThemeReference:
    """AE-0271: the create path accepts root key | "auto" | custom-palette UUID."""

    def test_accepts_root_key(self) -> None:
        assert validate_theme_reference("plasma_magenta") == "plasma_magenta"

    def test_accepts_auto(self) -> None:
        assert validate_theme_reference("auto") == "auto"

    def test_accepts_custom_palette_uuid(self) -> None:
        ref = str(uuid4())
        assert validate_theme_reference(ref) == ref

    def test_rejects_arbitrary_string(self) -> None:
        with pytest.raises(ValueError, match="root key"):
            validate_theme_reference("not_a_theme_or_uuid")
