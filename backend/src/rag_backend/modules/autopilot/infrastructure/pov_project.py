"""Carousel fields of an autopilot POV run (AE-0377, split from the driver)."""

from __future__ import annotations

from typing import TypedDict

from rag_backend.domain.constants.content_mode import (
    CONTENT_MODE_POV,
    DEFAULT_POV_FORMAT,
)
from rag_backend.domain.constants.presentation_policy import (
    CREATE_TIME_NEWS_PRESENTATION_POLICY_VERSION,
    CREATE_TIME_POV_PRESENTATION_POLICY_VERSION,
)
from rag_backend.modules.autopilot.domain.gate import ProjectSpec


class PovFields(TypedDict):
    pov_thesis: str | None
    pov_format: str | None


def _is_pov(spec: ProjectSpec) -> bool:
    return spec.content_mode == CONTENT_MODE_POV


def policy_version_for(spec: ProjectSpec) -> str:
    if _is_pov(spec):
        return CREATE_TIME_POV_PRESENTATION_POLICY_VERSION
    return CREATE_TIME_NEWS_PRESENTATION_POLICY_VERSION


def pov_fields_for(spec: ProjectSpec) -> PovFields:
    if not _is_pov(spec):
        return PovFields(pov_thesis=None, pov_format=None)
    return PovFields(pov_thesis=spec.pov_thesis, pov_format=DEFAULT_POV_FORMAT)


__all__ = ["PovFields", "policy_version_for", "pov_fields_for"]
