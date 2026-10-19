#!/usr/bin/env python3
"""Blog-v1 dead-code regression guard (AE-0428).

AE-0428 removed the v1 carousel-blog surface end-to-end: the ``blog_image_map``
key, the v1 blog i18n/with-design schemas and types, the dead frontend
components/hooks/constants, and the ``cleanup_blog_markdown`` helper (with its
package). This static check fails the build if any of those symbols reappears in
backend or frontend source, so a future PR cannot silently reintroduce the
regression that AE-0428 cleaned up.

Scope: ``backend/src`` (``.py``) and ``frontend/src`` (``.ts``/``.tsx``) code
only — prompt ``.yaml``/``.md`` files are frozen and excluded (they may still
mention ``blog_image_map``; the parser ignores it).

Usage:
    python scripts/check_blog_v1_dead_code.py [DIR ...]
Exits 1 (and prints each violation) if any forbidden token is found, else 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_ROOTS = (
    _REPO_ROOT / "backend" / "src",
    _REPO_ROOT / "frontend" / "src",
)
_CODE_SUFFIXES = (".py", ".ts", ".tsx")

# Unambiguous v1 symbol / file tokens. Chosen so a live same-name symbol is NOT
# matched: the live `useCarouselProject` (editorial), `BlogPostFilters` type and
# `CarouselSlideResponse` are deliberately absent.
#
# Each entry is (token, scope). Scope ``all`` matches backend + frontend; scope
# ``frontend`` matches frontend only — used for the two type names that ALSO
# exist as live BACKEND API schemas (`CarouselBlogI18nResponse`,
# `CarouselBlogWithDesignResponse` in `api/schemas/carousel.py`); only their
# frontend duplicates were deleted.
FORBIDDEN_TOKENS: tuple[tuple[str, str], ...] = (
    ("blog_image_map", "all"),
    ("cleanup_blog_markdown", "all"),
    ("CarouselBlogImageMapEntry", "all"),
    ("carouselBlogI18nResponseSchema", "all"),
    ("carouselBlogWithDesignResponseSchema", "all"),
    ("fetchBlogWithDesignCombined", "all"),
    ("mapProjectToBlogPostCard", "all"),
    ("useCarouselBlogWithDesign", "all"),
    ("use-accessibility-check", "all"),
    ("use-seo-analysis", "all"),
    ("use-editor-shortcuts", "all"),
    ("editor-shortcuts", "all"),
    ("use-carousel-blog", "all"),
    ("accessibility-checker", "all"),
    ("blog-post-filters", "all"),
    ("blog-post-admin-panel", "all"),
    ("image-gen-modal", "all"),
    ("keyboard-shortcuts-help", "all"),
    ("seo-preview", "all"),
    ("AccessibilityChecker", "all"),
    ("BlogPostAdminPanel", "all"),
    ("ImageGenModal", "all"),
    ("KeyboardShortcutsHelp", "all"),
    ("SeoPreview", "all"),
    ("useAccessibilityCheck", "all"),
    ("useEditorShortcuts", "all"),
    ("useSeoAnalysis", "all"),
    ("CarouselBlogI18nResponse", "frontend"),
    ("CarouselBlogWithDesignResponse", "frontend"),
)


def _is_frontend(path: Path) -> bool:
    return "frontend" in path.parts


def _tokens_for(path: Path) -> tuple[str, ...]:
    if _is_frontend(path):
        return tuple(token for token, _ in FORBIDDEN_TOKENS)
    return tuple(token for token, scope in FORBIDDEN_TOKENS if scope == "all")


def _iter_code_files(roots: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix in _CODE_SUFFIXES:
                files.append(path)
    return files


def find_violations(roots: tuple[Path, ...]) -> list[tuple[Path, int, str, str]]:
    violations: list[tuple[Path, int, str, str]] = []
    for path in _iter_code_files(roots):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            for token in _tokens_for(path):
                if token in line:
                    violations.append((path, number, token, line.strip()[:80]))
    return violations


def main(argv: list[str]) -> int:
    roots = tuple(Path(a) for a in argv) if argv else _DEFAULT_ROOTS
    violations = find_violations(roots)
    if not violations:
        print("OK: no blog-v1 dead code found.")
        return 0
    print("ERROR: blog-v1 dead code found (removed in AE-0428):")
    for path, line, token, snippet in violations:
        try:
            rel = path.relative_to(_REPO_ROOT)
        except ValueError:
            rel = path
        print(f"  {rel}:{line}: {token!r} in {snippet!r}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
