"""Rule-fires regression test for the anti-hardcoded-prompt checker (AE-0244/AE-0180).

Proves the checker FIRES on a seeded inline prompt (non-zero exit) and PASSES a
control that contains only a guarded `*_FALLBACK` constant + a docstring — not
merely that the real tree happens to pass.
"""

from __future__ import annotations

from pathlib import Path

from scripts.check_inline_prompts import find_violations, main

_INLINE_PROMPT_FILE = '''\
"""Module docstring — not a prompt, must be ignored."""


def build() -> str:
    return f"""You are a helpful assistant.

INSTRUCTIONS: do the thing.

OUTPUT FORMAT: json only.
"""
'''

_FALLBACK_ONLY_FILE = '''\
"""Module docstring with the marker You are here — ignored as a docstring."""

# A guarded registry-fallback constant is allowed (name contains FALLBACK).
_THING_FALLBACK = (
    "You are a helpful assistant.\\n"
    "INSTRUCTIONS: registry unavailable — load the registry file."
)
'''


def test_checker_fires_on_seeded_inline_prompt(tmp_path: Path) -> None:
    (tmp_path / "offender.py").write_text(_INLINE_PROMPT_FILE, encoding="utf-8")

    violations = find_violations((tmp_path,))
    assert violations, "checker must flag the seeded inline f-string prompt"
    assert main([str(tmp_path)]) == 1


def test_checker_passes_guarded_fallback_and_docstring(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text(_FALLBACK_ONLY_FILE, encoding="utf-8")

    assert find_violations((tmp_path,)) == []
    assert main([str(tmp_path)]) == 0


def test_checker_passes_empty_dir(tmp_path: Path) -> None:
    assert main([str(tmp_path)]) == 0
