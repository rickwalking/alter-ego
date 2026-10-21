"""Variable slide count and slide roles.

Gherkin: tests/features/carousel_variable_slide_count.feature
"""

from __future__ import annotations

from dataclasses import replace

import pytest
import yaml

from rag_backend.application.services.carousel.outline_normalize import (
    normalize_editorial_outline,
    outline_has_roles,
    stamp_outline_roles,
)
from rag_backend.application.services.carousel.presentation_deck_rules import (
    deck_violations,
)
from rag_backend.application.services.carousel.presentation_policy import (
    _parse_policy_document,
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_policy_range import (
    ERR_SLIDE_COUNT_OUT_OF_RANGE,
    expand_policy_for_count,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    PresentationPolicyError,
)
from rag_backend.application.services.carousel.project_policy import (
    create_time_policy_version,
    project_policy,
    project_slide_count,
)
from rag_backend.domain.constants.presentation_policy import (
    ERR_PRESENTATION_POLICY_INVALID,
)
from rag_backend.domain.constants.runtime_skills import (
    CAROUSEL_PIPELINE_SKILL_ID,
    resolve_runtime_skill_filesystem_path,
)
from rag_backend.domain.models import CarouselProject

_POV = "pov_hook_v1"
_V4 = "hero_lower_third_v4"


def _roles(policy) -> list[str | None]:
    return [slide.role for slide in policy.slides]


def _raw(version: str) -> dict[str, object]:
    path = resolve_runtime_skill_filesystem_path(
        CAROUSEL_PIPELINE_SKILL_ID, "contracts", f"{version}.yaml"
    )
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.unit
class TestLoader:
    # Scenario: Fixed contracts are unchanged
    def test_v3_is_fixed_without_roles(self) -> None:
        policy = load_presentation_policy("hero_lower_third_v3")
        assert policy.slide_range.minimum == policy.slide_range.maximum == 7
        assert policy.slide_count_range is None
        assert not policy.has_roles
        assert expand_policy_for_count(policy, 7) is policy

    # Scenario Outline: POV deck sizes
    @pytest.mark.parametrize(("count", "points"), [(8, 2), (9, 3), (10, 4)])
    def test_pov_sizes(self, count: int, points: int) -> None:
        policy = expand_policy_for_count(load_presentation_policy(_POV), count)
        roles = _roles(policy)
        assert policy.slide_count == count == len(policy.slides)
        assert roles.count("point") == points
        assert roles[:3] == ["hook", "rehook", "pov"]
        assert roles[-3:] == ["twist", "save", "cta"]
        assert [s.slide_number for s in policy.slides] == list(range(1, count + 1))
        assert policy.artwork_slides == tuple(range(4, 4 + points))

    def test_pov_range_and_default(self) -> None:
        span = load_presentation_policy(_POV).slide_range
        assert (span.minimum, span.maximum, span.default) == (8, 10, 9)

    # Scenario: Radar IA v4 with the optional twist
    def test_v4_seven_slides(self) -> None:
        policy = expand_policy_for_count(load_presentation_policy(_V4), 7)
        assert _roles(policy) == [
            "hook",
            "news",
            "impact",
            "impact",
            "impact",
            "verdict",
            "cta",
        ]
        assert policy.artwork_slides == (1, 3, 4, 5)
        assert [s.slide_type for s in policy.slides][-2:] == ["closing", "cta"]

    def test_v4_eight_slides_has_the_twist(self) -> None:
        policy = expand_policy_for_count(load_presentation_policy(_V4), 8)
        assert _roles(policy)[5] == "twist"

    # Scenario: Expanding outside the range fails
    @pytest.mark.parametrize("count", [7, 11])
    def test_out_of_range(self, count: int) -> None:
        with pytest.raises(PresentationPolicyError, match=ERR_SLIDE_COUNT_OUT_OF_RANGE):
            expand_policy_for_count(load_presentation_policy(_POV), count)


def _broken(change: str) -> dict[str, object]:
    document = _raw(_POV)
    slides = document["slide_sequence"]
    assert isinstance(slides, list)
    edits = {
        "unknown-role": lambda: slides[1].update(role="villain"),
        "role-type-mismatch": lambda: slides[0].update(role="save"),
        "partial-roles": lambda: slides[2].pop("role"),
        "min-above-max": lambda: document.update(slide_count_min=11),
        "max-not-sequence": lambda: document.update(slide_count_max=9),
        "optional-without-range": lambda: [
            document.pop("slide_count_min"),
            document.pop("slide_count_max"),
        ],
        "too-few-optional": lambda: slides[5].update(optional=False),
        "min-without-max": lambda: document.pop("slide_count_max"),
        "non-int-min": lambda: document.update(slide_count_min="8"),
    }
    edits[change]()
    return document


@pytest.mark.unit
@pytest.mark.parametrize(
    "change",
    [
        "unknown-role",
        "role-type-mismatch",
        "partial-roles",
        "min-above-max",
        "max-not-sequence",
        "optional-without-range",
        "too-few-optional",
        "min-without-max",
        "non-int-min",
    ],
)
def test_invalid_ranged_contracts_are_rejected(change: str) -> None:
    """Scenario Outline: Invalid ranged contracts are rejected."""
    with pytest.raises(PresentationPolicyError, match=ERR_PRESENTATION_POLICY_INVALID):
        _parse_policy_document(_broken(change), "raw")


@pytest.mark.unit
class TestProjectPolicy:
    # Scenario: Projects are stamped by mode
    def test_create_time_versions(self) -> None:
        assert create_time_policy_version("pov") == _POV
        assert create_time_policy_version("news_analysis") == _V4
        assert create_time_policy_version(None) == _V4

    # Scenario: A project's policy is sized to its slide count
    def test_sized_to_the_project(self) -> None:
        project = CarouselProject(topic="t", audience="a", niche="n")
        project.presentation_policy_version = _POV
        project.slide_count = 8
        assert project_policy(project).slide_count == 8

    def test_default_when_missing_or_out_of_range(self) -> None:
        project = CarouselProject(topic="t", audience="a", niche="n")
        project.presentation_policy_version = _POV
        assert project_policy(project).slide_count == 9
        project.slide_count = 12
        policy = load_presentation_policy(_POV)
        assert project_slide_count(project, policy) == 9

    def test_unstamped_project_uses_the_fixed_default(self) -> None:
        project = CarouselProject(topic="t", audience="a", niche="n")
        assert project_policy(project).slide_count == 7


def _outline(count: int, **extra: object) -> list[dict[str, object]]:
    return [
        {"slide_index": i, "title": f"Titulo {i}", "key_points": ["Ponto"], **extra}
        for i in range(1, count + 1)
    ]


@pytest.mark.unit
class TestOutlineNormalization:
    # Scenario: Legacy outline unchanged
    def test_legacy_outline_is_trimmed_to_seven(self) -> None:
        normalized = normalize_editorial_outline(_outline(9))
        assert len(normalized) == 7
        assert [s["slide_type"] for s in normalized] == [
            "intro",
            "summary",
            "content",
            "content",
            "content",
            "closing",
            "cta",
        ]
        assert all("role" not in s for s in normalized)

    # Scenario: Roles are stamped by position, never taken from the model
    def test_roles_are_stamped_by_position(self) -> None:
        policy = expand_policy_for_count(load_presentation_policy(_POV), 9)
        outline = _outline(9, role="news", slide_type="cta")
        outline[3].pop("role")
        stamped = stamp_outline_roles(outline, policy)
        assert [s["role"] for s in stamped] == _roles(policy)
        assert [s["slide_type"] for s in stamped] == [
            s.slide_type for s in policy.slides
        ]
        assert outline_has_roles(stamped)

    def test_stamping_drops_extra_slides(self) -> None:
        policy = expand_policy_for_count(load_presentation_policy(_POV), 8)
        assert len(stamp_outline_roles(_outline(10), policy)) == 8

    def test_stamping_ignores_contracts_without_roles(self) -> None:
        outline = _outline(7)
        policy = load_presentation_policy("hero_lower_third_v3")
        assert stamp_outline_roles(outline, policy) is outline

    # Scenario: Role outline keeps roles up to 10 slides
    def test_role_outline_keeps_ten(self) -> None:
        """The model returned 11 slides; stamping keeps the contract's 10."""
        policy = load_presentation_policy(_POV)
        stamped = stamp_outline_roles(_outline(11), policy)
        normalized = normalize_editorial_outline(stamped)
        assert len(normalized) == 10
        assert [s["role"] for s in normalized] == _roles(policy)
        assert normalized[0]["slide_type"] == "intro"
        assert normalized[8]["slide_type"] == "summary"

    def test_role_with_a_foreign_type_gets_its_role_type(self) -> None:
        normalized = normalize_editorial_outline([
            {"title": "Gancho", "role": "hook", "slide_type": "summary"}
        ])
        assert normalized[0]["slide_type"] == "intro"

    def test_one_unknown_role_falls_back_to_legacy(self) -> None:
        outline = _outline(3, role="hook")
        outline[1]["role"] = "villain"
        assert not outline_has_roles(outline)
        assert "role" not in normalize_editorial_outline(outline)[0]


@pytest.mark.unit
class TestDeckRule:
    # Scenario: Outline too long
    def test_pov_deck_of_eleven(self) -> None:
        violations = deck_violations([{}] * 11, load_presentation_policy(_POV))
        assert [v.code for v in violations] == ["slide_count_invalid"]
        assert violations[0].is_blocker

    @pytest.mark.parametrize("count", [8, 9, 10])
    def test_pov_deck_in_range(self, count: int) -> None:
        """The POV rubric may fire on an empty deck; the size rule must not."""
        codes = {
            v.code
            for v in deck_violations([{}] * count, load_presentation_policy(_POV))
        }
        assert "slide_count_invalid" not in codes

    # Scenario: Legacy decks never get the deck rule
    def test_legacy_deck_is_not_checked(self) -> None:
        policy = load_presentation_policy("hero_lower_third_v3")
        assert deck_violations([{}] * 6, policy) == []

    def test_fixed_contract_with_roles_uses_slide_count(self) -> None:
        policy = replace(load_presentation_policy(_V4), slide_count_range=None)
        assert [v.code for v in deck_violations([{}] * 9, policy)] == [
            "slide_count_invalid"
        ]


@pytest.mark.unit
class TestSlideFileOrder:
    """Generated slide images sort numerically (slide_10 after slide_9)."""

    def test_numeric_order(self, tmp_path) -> None:
        from rag_backend.application.services.carousel import (
            editorial_visual_pipeline as pipeline,
        )

        images = tmp_path / "images"
        images.mkdir()
        for number in (10, 2, 1, 9):
            (images / f"slide_{number}.jpg").write_bytes(b"x")
        (images / "slide_x.jpg").write_bytes(b"x")
        names = [
            p.name
            for p in sorted(images.glob("*.jpg"), key=pipeline._slide_file_number)
        ]
        assert names == [
            "slide_x.jpg",
            "slide_1.jpg",
            "slide_2.jpg",
            "slide_9.jpg",
            "slide_10.jpg",
        ]
