"""Inputs of the "Ponto de Vista" prompts (AE-0375, ADR-0021).

Plain data in the domain layer so both the agents and the application
generators can use them without an agents <-> application import: the caller
resolves the contract, the roles and the policy context and passes them in.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True)
class PovThesis:
    """The owner's thesis and proof; the model may sharpen, never invent."""

    thesis: str
    personal_proof: str = ""
    pov_format: str = ""


@dataclass(frozen=True, kw_only=True)
class PovOutlineRequest:
    """One POV outline: the brief, the owner's thesis and the contract roles."""

    topic: str
    audience: str
    brief: str
    sources: list[str] = field(default_factory=list)
    pov: PovThesis
    roles: tuple[str, ...]
    policy_context: str = ""


@dataclass(frozen=True, kw_only=True)
class PovHookRequest:
    """Five slide-1 hook candidates for a thesis."""

    topic: str
    audience: str
    pov: PovThesis


@dataclass(frozen=True, kw_only=True)
class RadarHookRequest:
    """AE-0376: five Radar IA slide-1 hooks from the brief and the sources."""

    topic: str
    audience: str
    brief: str
    sources: list[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class PovSlideContext:
    """What a POV slide draft needs beyond the generic slide inputs."""

    pov: PovThesis
    role: str
    slide_count: int
    hook_text: str = ""
    cta_copy: str = ""


@dataclass(frozen=True, kw_only=True)
class SlidePolicyContext:
    """The project's contract for a slide draft (role contracts only).

    ``pov`` is set for "Ponto de Vista" projects; Radar IA v4 drafts pass only
    the policy version and deck size so the instruction uses the right map.
    """

    policy_version: str
    slide_count: int
    pov: PovSlideContext | None = None
    # The sized contract rendered for the prompt (the caller sizes it).
    policy_context: str = ""
    # AE-0376: the contract's roles in order (outline) or this slide's role and
    # the chosen hook (content), for the Radar IA v7 prompts.
    roles: tuple[str, ...] = ()
    role: str = ""
    hook_text: str = ""


@dataclass(frozen=True, kw_only=True)
class SizedOutlineRequest:
    """One outline call (Radar IA): the brief, its sources and optional sizing.

    ``sizing`` is None for the legacy fixed contract (v1-v3).
    """

    topic: str
    audience: str
    brief: str
    sources: list[str] = field(default_factory=list)
    sizing: SlidePolicyContext | None = None


__all__ = [
    "PovHookRequest",
    "PovOutlineRequest",
    "PovSlideContext",
    "PovThesis",
    "RadarHookRequest",
    "SizedOutlineRequest",
    "SlidePolicyContext",
]
