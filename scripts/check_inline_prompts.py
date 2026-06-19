#!/usr/bin/env python3
"""Anti-hardcoded-prompt checker (AE-0244).

CLAUDE.md mandates "prompts live in `.md`/`.yaml`, never in `.py`" — loaded via
`agents.prompts.registry`. This static check flags **inline multi-line prompt
strings** in `backend/src/rag_backend/agents/` and `application/services/` so a
future PR cannot silently reintroduce one (the regression AE-0243 cleaned up).

A string is a violation when it is multi-line (contains a newline) AND contains a
prompt marker ("You are ", "INSTRUCTIONS:", "OUTPUT FORMAT", "Format your
response", "Hard rules:") — covering both plain `Constant` strings and f-strings
(`JoinedStr`, the exact AE-0243 pattern of an inline triple-quoted f-string
returned from a function).

Allowed (NOT flagged):
- **Docstrings** (module/class/function), which are not prompts.
- **Guarded inline-fallback constants** — a string assigned to a module/class
  constant whose name contains ``FALLBACK`` or ``TEMPLATE``. This is the
  sanctioned registry-fallback convention already in the tree
  (``_FALLBACK_SYSTEM_PROMPT``, ``_ALTER_EGO_FALLBACK_PROMPT``,
  ``IMAGE_PROMPT_REWRITE_TEMPLATE``, ``DESIGN_PROMPT_TEMPLATE``). The primary
  regression vector — an inline prompt returned/passed directly inside a function
  with no constant name — has no such name and is always flagged.

Usage:
    python scripts/check_inline_prompts.py [DIR ...]
Exits 1 (and prints each violation) if any inline prompt is found, else 0.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DIRS = (
    _REPO_ROOT / "backend" / "src" / "rag_backend" / "agents",
    _REPO_ROOT / "backend" / "src" / "rag_backend" / "application" / "services",
)

PROMPT_MARKERS = (
    "You are ",
    "INSTRUCTIONS:",
    "OUTPUT FORMAT",
    "Format your response",
    "Hard rules:",
)
_ALLOWED_NAME_TOKENS = ("FALLBACK", "TEMPLATE")


def _looks_like_prompt(text: str) -> bool:
    return "\n" in text and any(marker in text for marker in PROMPT_MARKERS)


def _joinedstr_static_text(node: ast.JoinedStr) -> str:
    """Concatenate the static (literal) parts of an f-string for marker testing."""
    parts: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
    return "".join(parts)


def _allowed_name(name: str) -> bool:
    upper = name.upper()
    return any(token in upper for token in _ALLOWED_NAME_TOKENS)


def _docstring_node_ids(tree: ast.AST) -> set[int]:
    """Object ids of Constant nodes that are docstrings (first stmt of a scope)."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            continue
        body = getattr(node, "body", [])
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            ids.add(id(body[0].value))
    return ids


def _allowed_value_ids(tree: ast.AST) -> set[int]:
    """Object ids of string/f-string values assigned to a FALLBACK/TEMPLATE name."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(t, ast.Name) and _allowed_name(t.id) for t in targets):
            if node.value is not None:
                ids.add(id(node.value))
    return ids


def find_violations(dirs: tuple[Path, ...]) -> list[tuple[Path, int, str]]:
    violations: list[tuple[Path, int, str]] = []
    for base in dirs:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if path.name.startswith("test_") or "/tests/" in str(path):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            skip = _docstring_node_ids(tree) | _allowed_value_ids(tree)
            for node in ast.walk(tree):
                if id(node) in skip:
                    continue
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    text = node.value
                elif isinstance(node, ast.JoinedStr):
                    text = _joinedstr_static_text(node)
                else:
                    continue
                if _looks_like_prompt(text):
                    first = text.strip().splitlines()[0][:60]
                    violations.append((path, node.lineno, first))
    return violations


def main(argv: list[str]) -> int:
    dirs = tuple(Path(a) for a in argv) if argv else _DEFAULT_DIRS
    violations = find_violations(dirs)
    if not violations:
        print("OK: no inline prompt strings found.")
        return 0
    print("ERROR: inline prompt string(s) found — move to the prompt registry")
    print("(agents/prompts/<domain>/v1/*.yaml via render_prompt), or, for a")
    print("genuine registry-fallback, name the constant *_FALLBACK / *_TEMPLATE:")
    for path, line, snippet in violations:
        try:
            rel = path.relative_to(_REPO_ROOT)
        except ValueError:
            rel = path
        print(f"  {rel}:{line}: {snippet!r}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
