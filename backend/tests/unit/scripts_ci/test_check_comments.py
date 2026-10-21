"""Rule-fires regression test for the backend comment policy gate.

Proves ``scripts/ci/check_comments.py`` FIRES on a seeded non-doc comment, a
ticket id, a to-do marker and a ticket id inside a docstring, and that it lets
docstrings, tool directives, shebangs and Gherkin references through.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import scripts.ci.check_comments as gate

_CLEAN = '''#!/usr/bin/env python3
"""Module docstring."""

import os  # noqa: F401
from a import (  # integrity-ok: baselined pair
    b,
)

# Scenario: A long scenario title that wraps over
#   two comment lines
def answer() -> int:  # pragma: no cover
    """Return the answer."""
    return 42  # type: ignore[return-value]
'''


def _reasons(source: str) -> list[str]:
    return [violation.reason for violation in gate.check_source("x.py", source)]


def test_clean_source_has_no_violations() -> None:
    assert gate.check_source("x.py", _CLEAN) == []


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        ("x = 1\n# explain the next line\ny = 2\n", gate._REASON_COMMENT),
        ("x = 1  # trailing note\n", gate._REASON_COMMENT),
        ("# x = old_code()\n", gate._REASON_COMMENT),
        ("x = 1  # noqa: E501 see AE-0123\n", gate._REASON_TICKET),
        ("x = 1  # noqa: E501 per D-6\n", gate._REASON_TICKET),
        ("x = 1  # pragma: no cover TODO drop\n", gate._REASON_MARKER),
        ('"""Module (AE-0001)."""\n', gate._REASON_TICKET),
        ('def f() -> None:\n    """FIXME later."""\n', gate._REASON_MARKER),
    ],
)
def test_seeded_violation_fires(source: str, reason: str) -> None:
    assert _reasons(source) == [reason]


def test_scenario_reference_may_repeat_a_ticket_id() -> None:
    source = "# Scenario: Fresh upgrade adds the AE-0371 schema\ndef t() -> None: ...\n"
    assert gate.check_source("x.py", source) == []


def test_docstring_scenario_line_may_repeat_a_ticket_id() -> None:
    source = 'def t() -> None:\n    """Scenario: Score is unscored (AE-0407)."""\n'
    assert gate.check_source("x.py", source) == []


def test_continuation_needs_a_scenario_line_directly_above() -> None:
    source = "# Scenario: Title\n\n#   not a continuation\n"
    assert _reasons(source) == [gate._REASON_COMMENT]


def test_unindented_line_after_a_scenario_is_not_a_continuation() -> None:
    source = "# Scenario: Title\n# a note riding on the reference\n"
    assert _reasons(source) == [gate._REASON_COMMENT]


def test_shebang_only_allowed_on_first_line() -> None:
    assert _reasons("x = 1\n#!/usr/bin/env python3\n") == [gate._REASON_COMMENT]


def test_main_exits_one_and_lists_the_violation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "bad.py").write_text("x = 1  # note\n", encoding="utf-8")
    monkeypatch.setattr(gate, "_REPO_ROOT", tmp_path)
    assert gate.main(["bad.py"]) == 1
    assert "bad.py:1: non-doc comment" in capsys.readouterr().out


def test_main_passes_a_clean_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "good.py").write_text(_CLEAN, encoding="utf-8")
    monkeypatch.setattr(gate, "_REPO_ROOT", tmp_path)
    assert gate.main(["good.py"]) == 0
    assert "comment policy OK" in capsys.readouterr().out


def test_default_scan_covers_backend_trees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = tmp_path / "backend"
    for relative in ("conf.py", "src/a.py", "tests/b.py", "alembic/c.py"):
        target = backend / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    monkeypatch.setattr(gate, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(gate, "_BACKEND", backend)
    assert gate._backend_files() == [
        "backend/conf.py",
        "backend/src/a.py",
        "backend/tests/b.py",
        "backend/alembic/c.py",
    ]
