"""Unit tests for the deterministic carousel repair pipeline (AE-0311).

Gherkin: tests/features/carousel_deterministic_repair.feature
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.carousel_repair_pipeline import (
    compute_localized_repairs,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
)

# The prod incident (project 38affb3e, slide 4): the raw drafting scaffold was
# stored verbatim as presentation_pt.body — long copy plus ``## PT`` / ``**Body:**``
# section labels. The deterministic pipeline must strip + trim it to clean copy.
_RAW_SCAFFOLD_BODY = (
    "## PT\n**Heading:** O disparo silencioso\n**Body:** A verdade incomoda: "
    "equipes tratam a regeneracao de conteudo como uma operacao segura, mas cada "
    "nova rodada reescreve artefatos ja aprovados pelo revisor humano. Quando o "
    "parser falha, o texto bruto inteiro vaza para o corpo visivel do slide e "
    "ninguem percebe ate a fase de design apontar as violacoes.\n**Features:**\n"
    "- Regeneracao segura\n## EN\n**Heading:** The silent regeneration\n**Body:** x."
)
_SCAFFOLD_LABELS = ("## PT", "## EN", "**Heading:**", "**Body:**", "**Features:**")
_V1 = PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1


def _scaffold_slide() -> dict[str, object]:
    return {
        "slide_index": 4,
        "slide_type": "content",
        "presentation_pt": {
            "slide_type": "content",
            "heading": "O disparo silencioso que corrompeu o slide quatro",
            "body": _RAW_SCAFFOLD_BODY,
        },
        "presentation_en": {
            "slide_type": "content",
            "heading": "The silent regeneration that corrupted slide four",
            "body": "The uncomfortable truth about regeneration leaking raw drafts.",
        },
    }


def _clean_slide() -> dict[str, object]:
    return {
        "slide_index": 1,
        "slide_type": "intro",
        "presentation_pt": {
            "slide_type": "intro",
            "heading": "Um titulo limpo",
            "body": "Um corpo curto e valido.",
        },
        "presentation_en": {
            "slide_type": "intro",
            "heading": "A clean title",
            "body": "A short valid body.",
        },
    }


class TestScaffoldRepair:
    """Scenario: repair a scaffold-contaminated slide (38affb3e regression)."""

    @pytest.mark.asyncio
    async def test_strips_scaffold_and_trims_body(self) -> None:
        computation = await compute_localized_repairs(
            [_scaffold_slide()], policy_version=_V1
        )
        assert computation.changed is True
        assert computation.blocking is False
        body = str(computation.repaired_slides[0]["presentation_pt"]["body"])
        assert all(label not in body for label in _SCAFFOLD_LABELS)
        assert body

    @pytest.mark.asyncio
    async def test_diff_reports_fixed_rule_codes(self) -> None:
        computation = await compute_localized_repairs(
            [_scaffold_slide()], policy_version=_V1
        )
        diff = next(d for d in computation.diffs if d.slide_index == 4)
        assert diff.repaired is True
        assert "drafting_scaffold_present" in diff.repaired_codes
        assert "body_too_long" in diff.repaired_codes
        assert diff.remaining_codes == ()


class TestIdempotency:
    """Scenario: a second repair on clean content is a no-op."""

    @pytest.mark.asyncio
    async def test_clean_slides_are_noop(self) -> None:
        computation = await compute_localized_repairs(
            [_clean_slide()], policy_version=_V1
        )
        assert computation.changed is False
        assert computation.diffs == ()
        assert computation.blocking is False

    @pytest.mark.asyncio
    async def test_repair_output_is_stable_on_second_pass(self) -> None:
        first = await compute_localized_repairs([_scaffold_slide()], policy_version=_V1)
        second = await compute_localized_repairs(
            first.repaired_slides, policy_version=_V1
        )
        assert second.changed is False


class TestUnrepairableHonesty:
    """Scenario: unrepairable violations are reported, not silently dropped."""

    @pytest.mark.asyncio
    async def test_missing_canonical_keys_stays_blocking(self) -> None:
        # A locale payload missing the canonical keys cannot be deterministically
        # rebuilt — it must remain blocking and be reported.
        broken = [
            {
                "slide_index": 3,
                "slide_type": "content",
                "presentation_pt": {"unexpected": "value"},
                "presentation_en": {"unexpected": "value"},
            }
        ]
        computation = await compute_localized_repairs(broken, policy_version=_V1)
        assert computation.blocking is True
        assert any(diff.remaining_codes for diff in computation.diffs)
