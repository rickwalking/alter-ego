"""Unit tests for carousel instruction context loader."""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.instruction_context_loader import (
    CarouselInstructionContextLoader,
    InstructionContextRequest,
    INSTRUCTION_CONTEXT_MAX_CHARS,
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
        assert "content-contracts.md" in result.instruction or "Content contracts" in result.instruction
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
