"""Phase subagent registry for carousel editorial orchestration (CP-005)."""

from __future__ import annotations

from dataclasses import dataclass

SUBAGENT_RESEARCH_SYNTHESIZER = "research_synthesizer"
SUBAGENT_OUTLINE_PLANNER = "outline_planner"
SUBAGENT_CONTENT_DRAFTER = "content_drafter"
SUBAGENT_CAPTION_WRITER = "caption_writer"

SKILL_ROOT = "skills/carousel-pipeline"


@dataclass(frozen=True)
class PhaseSubagentSpec:
    """DeepAgents CompiledSubAgent metadata with scoped skills."""

    name: str
    description: str
    phase_skill: str
    shared_standards: tuple[str, ...]


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
    """Return subagent metadata for DeepAgents registration."""
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "skills": [spec.phase_skill, *spec.shared_standards],
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
