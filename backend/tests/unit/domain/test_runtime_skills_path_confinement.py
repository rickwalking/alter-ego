"""Unit tests for runtime skill path confinement."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_backend.domain.constants.runtime_skills import read_runtime_skill_markdown


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
