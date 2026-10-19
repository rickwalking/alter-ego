"""Rule-fires regression test for the blog-v1 dead-code guard (AE-0428/AE-0180).

Proves the checker FIRES on a seeded v1 symbol (non-zero exit, naming the file)
and PASSES clean code — not merely that the real tree happens to pass. Also
proves the frontend-only type tokens do not flag the live backend schemas of the
same name.
"""

from __future__ import annotations

from pathlib import Path

from scripts.check_blog_v1_dead_code import find_violations, main

_SEEDED = "const x = payload.blog_image_map;\n"
_CLEAN = "export const OK = 1;\n"


def test_guard_fires_on_seeded_v1_symbol(
    tmp_path: Path, capsys: object
) -> None:
    offender = tmp_path / "offender.ts"
    offender.write_text(_SEEDED, encoding="utf-8")

    violations = find_violations((tmp_path,))
    assert violations, "guard must flag the seeded blog_image_map reference"
    assert main([str(tmp_path)]) == 1

    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "offender.ts" in out
    assert "blog_image_map" in out


def test_guard_passes_clean_code(tmp_path: Path) -> None:
    (tmp_path / "clean.ts").write_text(_CLEAN, encoding="utf-8")
    (tmp_path / "clean.py").write_text("OK = 1\n", encoding="utf-8")

    assert find_violations((tmp_path,)) == []
    assert main([str(tmp_path)]) == 0


def test_guard_passes_empty_dir(tmp_path: Path) -> None:
    assert main([str(tmp_path)]) == 0


def test_frontend_only_token_ignores_backend_schema(tmp_path: Path) -> None:
    """`CarouselBlogI18nResponse` is a LIVE backend schema — not a violation."""
    backend = tmp_path / "backend" / "src"
    backend.mkdir(parents=True)
    (backend / "schemas.py").write_text(
        "class CarouselBlogI18nResponse: ...\n", encoding="utf-8"
    )
    frontend = tmp_path / "frontend" / "src"
    frontend.mkdir(parents=True)
    (frontend / "carousel.ts").write_text(
        "type CarouselBlogI18nResponse = unknown;\n", encoding="utf-8"
    )

    violations = find_violations((tmp_path,))
    flagged = {path.name for path, *_ in violations}
    assert "schemas.py" not in flagged
    assert "carousel.ts" in flagged
