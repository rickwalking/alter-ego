"""Runtime skill path resolution for packaged and local development."""

from __future__ import annotations

import os
from pathlib import Path

ENV_RUNTIME_SKILLS_ROOT = "ALTER_EGO_RUNTIME_SKILLS_ROOT"
DEFAULT_RUNTIME_SKILLS_ROOT = "skills/runtime"
CAROUSEL_PIPELINE_SKILL_ID = "carousel-pipeline"
RUNTIME_PIPELINE_MARKER = Path("skills") / "runtime" / "carousel-pipeline"
PHASE_SKILL_FILENAME = "SKILL.md"


def get_runtime_skills_root() -> str:
    """Return configured runtime skills root or repository default."""
    return os.environ.get(ENV_RUNTIME_SKILLS_ROOT, DEFAULT_RUNTIME_SKILLS_ROOT)


def find_repository_root(start: Path | None = None) -> Path:
    """Locate repository root by walking parents for the runtime pipeline marker."""
    candidates = [start] if start is not None else []
    candidates.extend(Path(__file__).resolve().parents)
    candidates.extend(Path.cwd().parents)
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / RUNTIME_PIPELINE_MARKER).is_dir():
            return candidate
    msg = "Could not locate repository root for runtime skills"
    raise FileNotFoundError(msg)


def get_runtime_skills_filesystem_root() -> Path:
    """Return filesystem path to the runtime skills root."""
    configured = Path(get_runtime_skills_root())
    if configured.is_absolute():
        return configured
    return find_repository_root() / configured


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
