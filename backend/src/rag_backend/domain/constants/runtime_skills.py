"""Runtime skill path resolution for packaged and local development."""

from __future__ import annotations

import os
from pathlib import Path

ENV_RUNTIME_SKILLS_ROOT = "ALTER_EGO_RUNTIME_SKILLS_ROOT"
# Logical addressing prefix used by resolve_runtime_skill_path() and stripped by the
# read helpers below. It is NOT a filesystem path — the runtime skills physically
# live inside the backend package (AE-0246); see get_runtime_skills_filesystem_root.
DEFAULT_RUNTIME_SKILLS_ROOT = "skills/runtime"
CAROUSEL_PIPELINE_SKILL_ID = "carousel-pipeline"
PHASE_SKILL_FILENAME = "SKILL.md"

# AE-0246: runtime skills are co-located inside the backend package at
# rag_backend/agents/skills/, so they ship with `COPY backend/src/ src/` and resolve
# package-relative (no repo-root discovery, identical local and in-image). This file
# is rag_backend/domain/constants/runtime_skills.py -> parents[2] == rag_backend.
_PACKAGE_SKILLS_ROOT = Path(__file__).resolve().parents[2] / "agents" / "skills"


def get_runtime_skills_root() -> str:
    """Return the logical runtime-skills addressing prefix."""
    return DEFAULT_RUNTIME_SKILLS_ROOT


def get_runtime_skills_filesystem_root() -> Path:
    """Return filesystem path to the co-located runtime skills root.

    Package-relative by default (AE-0246). An ABSOLUTE
    ``ALTER_EGO_RUNTIME_SKILLS_ROOT`` override still wins (tests / custom layouts);
    a relative or unset value falls back to the packaged location.
    """
    override = os.environ.get(ENV_RUNTIME_SKILLS_ROOT)
    if override and Path(override).is_absolute():
        return Path(override)
    return _PACKAGE_SKILLS_ROOT


def resolve_runtime_skill_path(skill_id: str, *parts: str) -> str:
    """Build a runtime skill path from logical identifier and optional subpaths."""
    segments = (get_runtime_skills_root(), skill_id, *parts)
    return "/".join(segments)


def resolve_runtime_skill_filesystem_path(skill_id: str, *parts: str) -> Path:
    """Return an absolute filesystem path under the runtime skills root."""
    return get_runtime_skills_filesystem_root() / skill_id / Path(*parts)


def _assert_runtime_path_confined(path: Path) -> Path:
    """Reject runtime skill paths that escape the configured root."""
    resolved = path.resolve()
    root = get_runtime_skills_filesystem_root().resolve()
    if not resolved.is_relative_to(root):
        msg = f"Runtime skill path escapes configured root: {path}"
        raise FileNotFoundError(msg)
    return resolved


def read_runtime_skill_markdown(logical_path: str) -> str:
    """Read a runtime skill markdown file from a logical skill directory path."""
    skill_dir = Path(logical_path)
    if skill_dir.is_absolute():
        path = _assert_runtime_path_confined(skill_dir / PHASE_SKILL_FILENAME)
    else:
        parts = skill_dir.parts
        relative_parts = parts[2:] if parts[:2] == ("skills", "runtime") else parts
        path = _assert_runtime_path_confined(
            get_runtime_skills_filesystem_root().joinpath(*relative_parts)
            / PHASE_SKILL_FILENAME
        )
    if not path.is_file():
        msg = f"Runtime skill file not found: {path}"
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8")


def read_runtime_shared_markdown(logical_path: str) -> str:
    """Read a shared runtime markdown file from a logical path."""
    file_path = Path(logical_path)
    if file_path.is_absolute():
        path = _assert_runtime_path_confined(file_path)
    else:
        parts = file_path.parts
        relative_parts = parts[2:] if parts[:2] == ("skills", "runtime") else parts
        path = _assert_runtime_path_confined(
            get_runtime_skills_filesystem_root().joinpath(*relative_parts)
        )
    if not path.is_file():
        msg = f"Runtime shared file not found: {path}"
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8")


def carousel_pipeline_root() -> str:
    """Return the carousel pipeline runtime skill root path."""
    return resolve_runtime_skill_path(CAROUSEL_PIPELINE_SKILL_ID)
