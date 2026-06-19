#!/usr/bin/env python3
"""Validate runtime/delivery skill boundary, frontmatter, and compatibility links."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
# AE-0246: runtime skills are co-located inside the backend package (they ship with
# the source, not via a separate Dockerfile COPY); root skills/ is delivery-only.
RUNTIME_DIR = REPO_ROOT / "backend" / "src" / "rag_backend" / "agents" / "skills"
DELIVERY_DIR = SKILLS_DIR / "delivery"

REQUIRED_DELIVERY_COMMANDS = (
    "planner-skill",
    "architect-skill",
    "developer-skill",
    "qa-agent",
    "ticket-writer-skill",
    "orchestrator-skill",
    "release-manager-skill",
)

ARCHITECT_MODES = ("validate", "research", "skeptical", "bugfix")

FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
NAME_PATTERN = re.compile(r"^name:\s*(\S+)", re.MULTILINE)


def _parse_frontmatter(skill_md: Path) -> str:
    content = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return ""
    return match.group(1)


def _validate_delivery_skill_file(
    skill_md: Path,
    seen_names: set[str],
    errors: list[str],
) -> None:
    folder = skill_md.parent.name
    frontmatter = _parse_frontmatter(skill_md)
    if not frontmatter:
        errors.append(f"Missing YAML frontmatter: {skill_md}")
        return

    name_match = NAME_PATTERN.search(frontmatter)
    if not name_match:
        errors.append(f"Missing name in frontmatter: {skill_md}")
        return

    name = name_match.group(1)
    if name != folder:
        errors.append(
            f"Frontmatter name '{name}' != folder '{folder}' in {skill_md}",
        )
    if name in seen_names:
        errors.append(f"Duplicate delivery skill name: {name}")
    seen_names.add(name)

    # NOTE: delivery skills are intentionally model-invocable (Skill tool), so
    # `disable-model-invocation: true` is NO LONGER required — it was removed from
    # the delivery skills on purpose (commit 04a883b6) so the orchestrator can
    # invoke developer-skill / qa-agent / etc. via the Skill tool. The boundary
    # this validator still enforces is structural: name==folder, no duplicates,
    # the required slash commands exist, runtime/delivery stay separate, and the
    # Dockerfile copies only runtime skills.


def _validate_delivery_skills(errors: list[str]) -> None:
    if not DELIVERY_DIR.is_dir():
        errors.append(f"Missing delivery skills directory: {DELIVERY_DIR}")
        return

    seen_names: set[str] = set()
    for skill_md in sorted(DELIVERY_DIR.glob("*/SKILL.md")):
        _validate_delivery_skill_file(skill_md, seen_names, errors)

    errors.extend(
        f"Missing delivery skill for slash command: {command}"
        for command in REQUIRED_DELIVERY_COMMANDS
        if command not in seen_names
    )


def _validate_runtime_skills(errors: list[str]) -> None:
    if not RUNTIME_DIR.is_dir():
        errors.append(f"Missing runtime skills directory: {RUNTIME_DIR}")
        return

    required_runtime = (
        RUNTIME_DIR / "carousel-pipeline" / "SKILL.md",
        RUNTIME_DIR / "carousel-refinement" / "SKILL.md",
    )
    errors.extend(
        f"Missing required runtime skill: {path}"
        for path in required_runtime
        if not path.is_file()
    )

    manifest = RUNTIME_DIR / "carousel-pipeline" / "bmad-skill-manifest.yaml"
    if manifest.is_file():
        manifest_text = manifest.read_text(encoding="utf-8")
        if "skills/delivery" in manifest_text:
            errors.append(f"Runtime manifest references delivery path: {manifest}")


def _validate_compatibility_links(errors: list[str]) -> None:
    for entry in SKILLS_DIR.iterdir():
        if not entry.is_symlink():
            continue
        target = entry.resolve()
        if not target.exists():
            errors.append(f"Broken compatibility link: {entry} -> {target}")
            continue
        if (
            entry.name in REQUIRED_DELIVERY_COMMANDS
            and DELIVERY_DIR not in target.parents
        ):
            errors.append(
                f"Delivery compatibility link must resolve under delivery/: {entry}",
            )


def _validate_dockerfile(errors: list[str]) -> None:
    dockerfile = REPO_ROOT / "backend" / "Dockerfile"
    if not dockerfile.is_file():
        errors.append("Missing backend/Dockerfile")
        return
    content = dockerfile.read_text(encoding="utf-8")
    # AE-0246: runtime skills ship inside the backend package (via `COPY backend/src/`),
    # not a separate `COPY skills/runtime/`. The image must still copy the source and
    # must never copy the delivery skills.
    if not re.search(r"COPY\s+(?:--\S+\s+)*backend/src/", content):
        errors.append("backend/Dockerfile must COPY backend/src/")
    if "skills/delivery" in content:
        errors.append("backend/Dockerfile must not COPY skills/delivery")


def validate_skill_boundary() -> list[str]:
    """Run all skill boundary checks and return error messages."""
    errors: list[str] = []
    _validate_delivery_skills(errors)
    _validate_runtime_skills(errors)
    _validate_compatibility_links(errors)
    _validate_dockerfile(errors)
    return errors


def main() -> int:
    errors = validate_skill_boundary()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"{len(errors)} skill boundary error(s)", file=sys.stderr)
        return 1
    print("Skill boundary validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
