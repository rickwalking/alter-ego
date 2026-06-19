"""Phase subagent registry for carousel editorial orchestration (CP-005)."""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.domain.constants.runtime_skills import carousel_pipeline_root

SUBAGENT_RESEARCH_SYNTHESIZER = "research_synthesizer"
SUBAGENT_OUTLINE_PLANNER = "outline_planner"
SUBAGENT_CONTENT_DRAFTER = "content_drafter"
SUBAGENT_CAPTION_WRITER = "caption_writer"

SKILL_ROOT = carousel_pipeline_root()

# DeepAgents subagent spec field names (the standard tools/prompt/model surface).
# AE-0249 aligns these phase specs to the DeepAgents fields; the half-wired
# ``skills``-only key is replaced by a ``prompt`` carrying the skill references.
SPEC_FIELD_NAME = "name"
SPEC_FIELD_DESCRIPTION = "description"
SPEC_FIELD_PROMPT = "prompt"
SPEC_FIELD_TOOLS = "tools"

PROMPT_SKILL_CONTEXT_HEADER = "Read the following skill context before acting:"


@dataclass(frozen=True)
class PhaseSubagentSpec:
    """DeepAgents CompiledSubAgent metadata with scoped skills."""

    name: str
    description: str
    phase_skill: str
    shared_standards: tuple[str, ...]

    def skill_references(self) -> tuple[str, ...]:
        """Return the skill markdown references this phase reads."""
        return (self.phase_skill, *self.shared_standards)

    def prompt(self) -> str:
        """Render the DeepAgents ``prompt`` from this phase's skill references."""
        references = "\n".join(f"- {ref}" for ref in self.skill_references())
        return f"{self.description}\n\n{PROMPT_SKILL_CONTEXT_HEADER}\n{references}"


PHASE_SUBAGENT_REGISTRY: tuple[PhaseSubagentSpec, ...] = (
    PhaseSubagentSpec(
        name=SUBAGENT_RESEARCH_SYNTHESIZER,
        description="Synthesize research findings from source materials.",
        phase_skill=f"{SKILL_ROOT}/phases/research",
        shared_standards=(
            f"{SKILL_ROOT}/_shared/critical-rules.md",
            f"{SKILL_ROOT}/_shared/anti-patterns.md",
        ),
    ),
    PhaseSubagentSpec(
        name=SUBAGENT_OUTLINE_PLANNER,
        description="Plan carousel slide outline from brief and research.",
        phase_skill=f"{SKILL_ROOT}/phases/outline",
        shared_standards=(
            f"{SKILL_ROOT}/_shared/critical-rules.md",
            f"{SKILL_ROOT}/_shared/text-formatting.md",
        ),
    ),
    PhaseSubagentSpec(
        name=SUBAGENT_CONTENT_DRAFTER,
        description="Draft slide copy with persona enforcement.",
        phase_skill=f"{SKILL_ROOT}/phases/content",
        shared_standards=(
            f"{SKILL_ROOT}/_shared/content-contracts.md",
            f"{SKILL_ROOT}/_shared/text-formatting.md",
            f"{SKILL_ROOT}/_shared/anti-patterns.md",
        ),
    ),
    PhaseSubagentSpec(
        name=SUBAGENT_CAPTION_WRITER,
        description="Write Instagram caption and export copy.",
        phase_skill=f"{SKILL_ROOT}/phases/final-review",
        shared_standards=(f"{SKILL_ROOT}/_shared/export-and-caption.md",),
    ),
)


def build_phase_subagent_specs() -> list[dict[str, object]]:
    """Return DeepAgents-aligned subagent specs (tools/prompt fields).

    AE-0249: emits the standard DeepAgents ``name``/``description``/``prompt``/
    ``tools`` fields. ``tools`` is empty here because these deterministic phases
    run as raw LangGraph nodes (ADR-007), not tool-wielding subagents.
    """
    return [
        {
            SPEC_FIELD_NAME: spec.name,
            SPEC_FIELD_DESCRIPTION: spec.description,
            SPEC_FIELD_PROMPT: spec.prompt(),
            SPEC_FIELD_TOOLS: [],
        }
        for spec in PHASE_SUBAGENT_REGISTRY
    ]


__all__ = [
    "PHASE_SUBAGENT_REGISTRY",
    "SUBAGENT_CAPTION_WRITER",
    "SUBAGENT_CONTENT_DRAFTER",
    "SUBAGENT_OUTLINE_PLANNER",
    "SUBAGENT_RESEARCH_SYNTHESIZER",
    "PhaseSubagentSpec",
    "build_phase_subagent_specs",
]
