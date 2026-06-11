"""Instruction context assembly for carousel editorial agents."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from rag_backend.application.services.carousel.phase_subagents import (
    PHASE_SUBAGENT_REGISTRY,
    SUBAGENT_CONTENT_DRAFTER,
    SUBAGENT_OUTLINE_PLANNER,
)
from rag_backend.application.services.carousel.presentation_policy import (
    CarouselPresentationPolicy,
    load_presentation_policy,
    render_presentation_policy_context,
)
from rag_backend.domain.constants.carousel import CAROUSEL_PROMPT_VERSION_V3
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_OUTLINE,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.constants.runtime_skills import (
    read_runtime_shared_markdown,
    read_runtime_skill_markdown,
)

INSTRUCTION_CHECKSUM_PREFIX = "sha256"
INSTRUCTION_CONTEXT_MAX_CHARS = 12000
INSTRUCTION_TRUNCATION_MARKER = "\n[instruction context truncated]\n"

SECTION_SAFETY = "## Safety and factual sources"
SECTION_POLICY = "## Presentation policy and schema"
SECTION_LOCALE = "## Locale rules"
SECTION_SLIDE = "## Slide constraints"
SECTION_PERSONA = "## Persona voice"
SECTION_REVISION = "## Reviewer revision notes"
SECTION_PHASE_SKILL = "## Phase skill"
SECTION_SHARED = "## Shared standards"

PHASE_TO_SUBAGENT: dict[str, str] = {
    PHASE_OUTLINE: SUBAGENT_OUTLINE_PLANNER,
    PHASE_CONTENT: SUBAGENT_CONTENT_DRAFTER,
}


@dataclass(frozen=True)
class InstructionContextRequest:
    """Inputs for bounded editorial instruction context assembly."""

    phase: str
    locale: str
    persona_context: str = ""
    revision_notes: str = ""
    slide_number: int | None = None
    policy_version: str = DEFAULT_PRESENTATION_POLICY_VERSION
    prompt_version: str = CAROUSEL_PROMPT_VERSION_V3


@dataclass(frozen=True)
class InstructionContextResult:
    """Bounded instruction payload plus trace metadata."""

    instruction: str
    checksum: str
    policy_version: str
    policy_checksum: str
    prompt_version: str
    phase: str
    slide_number: int | None


class CarouselInstructionContextLoader:
    """Load phase skills, shared standards, and policy into one instruction string."""

    def load(self, request: InstructionContextRequest) -> InstructionContextResult:
        """Build bounded instruction context for an editorial phase."""
        policy = load_presentation_policy(request.policy_version)
        sections = [
            SECTION_SAFETY,
            _safety_block(),
            SECTION_POLICY,
            render_presentation_policy_context(policy),
            _schema_block(request.prompt_version),
            SECTION_LOCALE,
            _locale_block(request.locale),
        ]
        slide_block = _slide_block(request.slide_number, policy)
        if slide_block:
            sections.extend([SECTION_SLIDE, slide_block])
        sections.extend([
            SECTION_PERSONA,
            request.persona_context.strip() or "Default professional voice.",
            SECTION_REVISION,
            request.revision_notes.strip() or "None.",
        ])
        phase_skill, shared_files = _phase_resources(request.phase)
        sections.extend([SECTION_PHASE_SKILL, phase_skill])
        for shared_path in shared_files:
            sections.extend([SECTION_SHARED, read_runtime_shared_markdown(shared_path)])
        instruction = _bound_instruction(
            "\n\n".join(section.strip() for section in sections if section)
        )
        return InstructionContextResult(
            instruction=instruction,
            checksum=_instruction_checksum(instruction),
            policy_version=policy.version,
            policy_checksum=policy.checksum,
            prompt_version=request.prompt_version,
            phase=request.phase,
            slide_number=request.slide_number,
        )


def _phase_resources(phase: str) -> tuple[str, tuple[str, ...]]:
    subagent_name = PHASE_TO_SUBAGENT.get(phase)
    if subagent_name is None:
        msg = f"Unsupported editorial phase for instruction context: {phase}"
        raise ValueError(msg)
    for spec in PHASE_SUBAGENT_REGISTRY:
        if spec.name == subagent_name:
            return read_runtime_skill_markdown(spec.phase_skill), spec.shared_standards
    msg = f"Phase subagent not registered: {subagent_name}"
    raise ValueError(msg)


def _bound_instruction(text: str) -> str:
    if len(text) <= INSTRUCTION_CONTEXT_MAX_CHARS:
        return text
    keep = INSTRUCTION_CONTEXT_MAX_CHARS - len(INSTRUCTION_TRUNCATION_MARKER)
    return text[:keep] + INSTRUCTION_TRUNCATION_MARKER


def _instruction_checksum(instruction: str) -> str:
    digest = sha256(instruction.encode("utf-8")).hexdigest()
    return f"{INSTRUCTION_CHECKSUM_PREFIX}-{digest}"


def _safety_block() -> str:
    return (
        "Use only supplied research sources for factual claims. "
        "Do not invent statistics, quotes, or URLs."
    )


def _schema_block(prompt_version: str) -> str:
    return (
        f"Structured output must follow carousel/{prompt_version} prompt schema. "
        "Return JSON only. Use icon_name with Lucide allowlist values."
    )


def _locale_block(locale: str) -> str:
    return (
        f"Active locale: {locale}. "
        "Maintain bilingual structural parity when generating paired PT/EN copy."
    )


def _slide_block(
    slide_number: int | None,
    policy: CarouselPresentationPolicy,
) -> str:
    if slide_number is None:
        return ""
    for slide in policy.slides:
        if slide.slide_number == slide_number:
            ratio = (
                f"copy_start_ratio={slide.copy_start_ratio}"
                if slide.copy_start_ratio is not None
                else "cta layout (no lower-third ratio)"
            )
            return (
                f"Target slide {slide.slide_number} ({slide.slide_type}). "
                f"Image required: {slide.image_required}. {ratio}."
            )
    return f"Target slide {slide_number}."


__all__ = [
    "CarouselInstructionContextLoader",
    "InstructionContextRequest",
    "InstructionContextResult",
]
