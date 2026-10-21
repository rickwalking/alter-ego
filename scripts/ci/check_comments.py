#!/usr/bin/env python3
"""Comment policy gate for backend Python sources.

Pedro's rule: source and test code carries no explanatory ``#`` comments. Docs
live in docstrings. A ``#`` comment is allowed only when a tool or gate reads it:

* a shebang on line 1 or an encoding declaration on lines 1-2;
* a tool directive (``noqa``, ``type: ignore``, ``pragma``, ``pyright:``,
  ``mypy:``, ``fmt:``, ``isort:``, ``ruff:``, ``nosec``, and the
  ``integrity-ok:`` escape hatch read by ``scripts/ci/check-integrity.sh``);
* a Gherkin reference read by ``scripts/check_gherkin_refs.py``
  (``# Scenario: <title>``), plus comment-only continuation lines that directly
  follow it when a long title wraps;
* a licence header (``SPDX-License-Identifier`` / ``Copyright``).

Ticket ids, decision ids and to-do markers (``_TICKET`` and ``_MARKER``)
are rejected in every remaining comment and in every docstring. A Gherkin
reference is exempt from the ticket-id check because it must repeat the
scenario title verbatim.

Usage:
    python scripts/ci/check_comments.py            # every backend .py
    python scripts/ci/check_comments.py FILE...    # just these files
Exits 1 and lists ``path:line: reason: comment`` for every violation.
"""

from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
_SCAN_DIRS = ("src", "tests", "scripts", "alembic")
_DIRECTIVE = re.compile(
    r"^#\s*(noqa\b|type:\s*ignore\b|pragma\b|pyright:|mypy:|fmt:\s*(off|on|skip)\b"
    r"|isort:|ruff:|nosec\b|integrity-ok:)"
)
_SCENARIO = re.compile(r"^#\s*Scenario(?: Outline)?:\s*\S")
_LICENCE = re.compile(r"^#\s*(SPDX-License-Identifier:|Copyright\b)")
_CODING = re.compile(r"^#.*coding[:=]")
_TICKET = re.compile(r"\b(?:AE-\d{2,5}|D-\d+)\b")
_MARKER = re.compile(r"\b(?:TODO|FIXME|XXX|HACK)\b")
_CODING_MAX_LINE = 2
_REASON_COMMENT = "non-doc comment (move real information into a docstring)"
_REASON_TICKET = "ticket or decision id"
_REASON_MARKER = "TODO/FIXME/XXX/HACK marker"


@dataclass(frozen=True)
class Violation:
    """One rejected comment or docstring."""

    path: str
    line: int
    reason: str
    text: str

    def render(self) -> str:
        """``path:line: reason: text`` (the text trimmed to one line)."""
        snippet = self.text.strip().splitlines()[0] if self.text.strip() else ""
        return f"{self.path}:{self.line}: {self.reason}: {snippet}"


def _is_standalone(token: tokenize.TokenInfo) -> bool:
    return not token.line[: token.start[1]].strip()


def _is_tool_comment(token: tokenize.TokenInfo) -> bool:
    text = token.string
    line = token.start[0]
    if line == 1 and text.startswith("#!"):
        return True
    if line <= _CODING_MAX_LINE and _CODING.match(text):
        return True
    return bool(_DIRECTIVE.match(text) or _LICENCE.match(text))


def _noise_reason(text: str) -> str | None:
    if _TICKET.search(text):
        return _REASON_TICKET
    if _MARKER.search(text):
        return _REASON_MARKER
    return None


def comment_violations(path: str, source: str) -> list[Violation]:
    """Every ``#`` comment in ``source`` that the policy rejects."""
    violations: list[Violation] = []
    scenario_line = -2
    readline = io.StringIO(source).readline
    for token in tokenize.generate_tokens(readline):
        if token.type != tokenize.COMMENT:
            continue
        line = token.start[0]
        standalone = _is_standalone(token)
        if standalone and _SCENARIO.match(token.string):
            scenario_line = line
            continue
        if standalone and line == scenario_line + 1:
            scenario_line = line
            continue
        if _is_tool_comment(token):
            reason = _noise_reason(token.string)
            if reason:
                violations.append(Violation(path, line, reason, token.string))
            continue
        violations.append(Violation(path, line, _REASON_COMMENT, token.string))
    return violations


def _docstring_nodes(tree: ast.Module) -> list[ast.Constant]:
    owners = [tree] + [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    nodes: list[ast.Constant] = []
    for owner in owners:
        body = owner.body
        if not body or not isinstance(body[0], ast.Expr):
            continue
        value = body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            nodes.append(value)
    return nodes


def docstring_violations(path: str, source: str) -> list[Violation]:
    """Docstrings in ``source`` that carry a ticket id or a to-do marker."""
    violations: list[Violation] = []
    for node in _docstring_nodes(ast.parse(source)):
        text = str(node.value)
        reason = _noise_reason(text)
        if reason is None:
            continue
        offending = next((row for row in text.splitlines() if _noise_reason(row)), text)
        violations.append(Violation(path, node.lineno, reason, offending))
    return violations


def check_source(path: str, source: str) -> list[Violation]:
    """All comment and docstring violations of one Python source."""
    return comment_violations(path, source) + docstring_violations(path, source)


def _backend_files() -> list[str]:
    files = sorted(_BACKEND.glob("*.py"))
    for directory in _SCAN_DIRS:
        files.extend(sorted((_BACKEND / directory).rglob("*.py")))
    return [path.relative_to(_REPO_ROOT).as_posix() for path in files]


def main(argv: list[str]) -> int:
    """Check the given files (or every backend .py); 1 on violations."""
    paths = argv or _backend_files()
    violations: list[Violation] = []
    for relative in paths:
        source = (_REPO_ROOT / relative).read_text(encoding="utf-8")
        violations.extend(check_source(relative, source))
    for violation in violations:
        print(violation.render())
    if violations:
        print(
            f"\n{len(violations)} comment policy violation(s). Only docstrings, "
            "tool directives and Gherkin 'Scenario:' references are allowed.",
            file=sys.stderr,
        )
        return 1
    print(f"comment policy OK ({len(paths)} Python files scanned).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
