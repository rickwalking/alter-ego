"""Unit tests for runtime skill path confinement."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_backend.domain.constants.runtime_skills import (
    get_runtime_skills_filesystem_root,
    read_runtime_skill_markdown,
)


def test_default_root_is_package_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    # AE-0246: with no override, runtime skills resolve INSIDE the backend package
    # (so they ship with the source and resolve identically in the built image).
    monkeypatch.delenv("ALTER_EGO_RUNTIME_SKILLS_ROOT", raising=False)
    root = get_runtime_skills_filesystem_root()
    assert root.parts[-2:] == ("agents", "skills")
    assert (root / "carousel-pipeline" / "SKILL.md").is_file()


def test_absolute_env_override_wins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ALTER_EGO_RUNTIME_SKILLS_ROOT", str(tmp_path))
    assert get_runtime_skills_filesystem_root() == tmp_path


def test_relative_env_override_falls_back_to_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A relative override is ignored (the old repo-root scheme is gone).
    monkeypatch.setenv("ALTER_EGO_RUNTIME_SKILLS_ROOT", "skills/runtime")
    assert get_runtime_skills_filesystem_root().parts[-2:] == ("agents", "skills")


def test_read_runtime_skill_rejects_escape_outside_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.setenv("ALTER_EGO_RUNTIME_SKILLS_ROOT", str(runtime_root))

    with pytest.raises(FileNotFoundError, match="escapes configured root"):
        read_runtime_skill_markdown(str(outside))
