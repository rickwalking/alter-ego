"""Unit tests for carousel instruction context loader."""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.instruction_context_loader import (
    INSTRUCTION_CONTEXT_MAX_CHARS,
    PREVIOUS_DRAFT_LABEL,
    REVISION_IMPERATIVE_HEADER,
    SECTION_SHARED,
    SECTION_SIBLING,
    CarouselInstructionContextLoader,
    InstructionContextRequest,
)
from rag_backend.domain.constants.carousel import CAROUSEL_PROMPT_VERSION_V3
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_OUTLINE,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
)


@pytest.mark.unit
class TestInstructionContextLoader:
    """Gherkin: Editorial agents receive bounded policy instruction context."""

    def test_outline_phase_loads_policy_and_shared_files(self) -> None:
        """WHEN outline phase loads THEN policy, phase skill, and shared docs are included."""
        loader = CarouselInstructionContextLoader()
        result = loader.load(
            InstructionContextRequest(
                phase=PHASE_OUTLINE,
                locale="pt-BR",
                persona_context="Direct founder voice.",
                revision_notes="Tighten slide 2 summary cards.",
            )
        )

        assert result.policy_version == PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
        assert result.prompt_version == CAROUSEL_PROMPT_VERSION_V3
        assert result.phase == PHASE_OUTLINE
        assert result.checksum.startswith("sha256-")
        assert result.policy_checksum.startswith("sha256-")
        assert "Presentation policy: hero_lower_third_v1" in result.instruction
        assert "Slide count: 7" in result.instruction
        assert "Em-dash ban" in result.instruction
        assert "Direct founder voice." in result.instruction
        assert "Tighten slide 2 summary cards." in result.instruction

    def test_content_phase_includes_slide_constraints(self) -> None:
        """WHEN content phase loads for a slide THEN slide constraints are included."""
        loader = CarouselInstructionContextLoader()
        result = loader.load(
            InstructionContextRequest(
                phase=PHASE_CONTENT,
                locale="en",
                slide_number=6,
            )
        )

        assert result.slide_number == 6
        assert "Target slide 6 (closing)" in result.instruction
        assert (
            "content-contracts.md" in result.instruction
            or "Content contracts" in result.instruction
        )
        assert "Lucide icon allowlist" in result.instruction

    def test_instruction_context_is_bounded(self) -> None:
        """WHEN shared docs are large THEN instruction remains within the configured cap."""
        loader = CarouselInstructionContextLoader()
        result = loader.load(
            InstructionContextRequest(
                phase=PHASE_CONTENT,
                locale="pt-BR",
                revision_notes="x" * 20000,
            )
        )

        assert len(result.instruction) <= INSTRUCTION_CONTEXT_MAX_CHARS

    def test_unsupported_phase_raises(self) -> None:
        """WHEN an unsupported phase loads THEN loader fails fast."""
        loader = CarouselInstructionContextLoader()
        with pytest.raises(ValueError, match="Unsupported editorial phase"):
            loader.load(InstructionContextRequest(phase="research", locale="pt-BR"))

    def test_sibling_context_is_rendered(self) -> None:
        """AE-0291: other slides' outline is injected so a slide can differentiate."""
        loader = CarouselInstructionContextLoader()
        result = loader.load(
            InstructionContextRequest(
                phase=PHASE_CONTENT,
                locale="pt-BR",
                slide_number=3,
                sibling_context="- Slide 2: Origins — history, roots",
            )
        )

        assert SECTION_SIBLING in result.instruction
        assert "- Slide 2: Origins — history, roots" in result.instruction

    def test_revision_notes_render_imperatively_with_previous_draft(self) -> None:
        """AE-0291: regeneration framing + previous draft, imperative header once."""
        loader = CarouselInstructionContextLoader()
        result = loader.load(
            InstructionContextRequest(
                phase=PHASE_CONTENT,
                locale="pt-BR",
                slide_number=3,
                revision_notes="Make it concrete.",
                previous_draft="The rejected copy.",
            )
        )

        assert result.instruction.count(REVISION_IMPERATIVE_HEADER) == 1
        assert "Make it concrete." in result.instruction
        assert PREVIOUS_DRAFT_LABEL in result.instruction
        assert "The rejected copy." in result.instruction

    def test_revision_and_sibling_survive_truncation_before_shared(self) -> None:
        """AE-0291: with an oversized shared blob, notes + sibling context survive
        because shared standards are ordered last and truncated first."""
        loader = CarouselInstructionContextLoader()
        result = loader.load(
            InstructionContextRequest(
                phase=PHASE_CONTENT,
                locale="pt-BR",
                slide_number=3,
                revision_notes="Keep this reviewer note.",
                sibling_context="Keep this sibling outline.",
            )
        )

        assert len(result.instruction) <= INSTRUCTION_CONTEXT_MAX_CHARS
        assert "Keep this reviewer note." in result.instruction
        assert "Keep this sibling outline." in result.instruction
        # Revision + sibling sections precede the shared-standards section.
        assert result.instruction.index(SECTION_SIBLING) < (
            result.instruction.index(SECTION_SHARED)
            if SECTION_SHARED in result.instruction
            else len(result.instruction)
        )
