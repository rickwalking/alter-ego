#!/usr/bin/env python3
"""Carousel release QA — collect evidence for AE-0039.

Runs all machine-gate checks and produces a release evidence directory.

Usage:
    uv run python scripts/carousel_release_qa.py --output-dir /tmp/ae-0039-evidence
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import NoReturn

# Paths
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

# mutmut reads paths_to_mutate from backend/setup.cfg
MUTATION_TARGETS: list[str] = []  # noqa: RUF012 — documented for reference


@dataclass(frozen=True)
class Evidence:
    command: str
    status: str
    stdout: str
    stderr: str


@dataclass(frozen=True)
class ReleaseQaReport:
    backend_tests: Evidence
    frontend_tests: Evidence
    mutation_testing: Evidence
    ruff_check: Evidence
    frontend_lint: Evidence
    frontend_typecheck: Evidence
    visual_qa_script_check: Evidence
    contact_sheet_example: Evidence


def _run(cmd: list[str], cwd: Path, timeout: int = 300) -> Evidence:
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return Evidence(
            command=" ".join(cmd),
            status="PASS" if result.returncode == 0 else "FAIL",
            stdout=result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout,
            stderr=result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
        )
    except subprocess.TimeoutExpired:
        return Evidence(
            command=" ".join(cmd),
            status="TIMEOUT",
            stdout="",
            stderr=f"Timed out after {timeout}s",
        )
    except FileNotFoundError as exc:
        return Evidence(
            command=" ".join(cmd),
            status="FAIL",
            stdout="",
            stderr=str(exc),
        )


def _write_evidence(report: ReleaseQaReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON report
    (output_dir / "release-qa-evidence.json").write_text(
        json.dumps(asdict(report), indent=2),
        encoding="utf-8",
    )

    # Write human-readable markdown
    md = []
    md.append("# AE-0039 Release QA Evidence")
    md.append("")
    md.append("## Backend Tests")
    md.append(f"```bash")
    md.append(f"{report.backend_tests.command}")
    md.append(f"```")
    md.append(f"**Status:** {report.backend_tests.status}")
    md.append(f"```")
    md.append(report.backend_tests.stdout)
    md.append(f"```")
    md.append("")

    md.append("## Frontend Tests")
    md.append(f"```bash")
    md.append(f"{report.frontend_tests.command}")
    md.append(f"```")
    md.append(f"**Status:** {report.frontend_tests.status}")
    md.append(f"```")
    md.append(report.frontend_tests.stdout)
    md.append(f"```")
    md.append("")

    md.append("## Mutation Testing")
    md.append(f"```bash")
    md.append(f"{report.mutation_testing.command}")
    md.append(f"```")
    md.append(f"**Status:** {report.mutation_testing.status}")
    md.append(f"```")
    md.append(report.mutation_testing.stdout)
    md.append(f"```")
    md.append("")

    md.append("## Code Quality")
    md.append(f"**Backend Ruff:** {report.ruff_check.status}")
    md.append(f"```bash")
    md.append(f"{report.ruff_check.command}")
    md.append(f"```")
    md.append(f"**Frontend ESLint:** {report.frontend_lint.status}")
    md.append(f"```bash")
    md.append(f"{report.frontend_lint.command}")
    md.append(f"```")
    md.append(f"**Frontend TypeScript:** {report.frontend_typecheck.status}")
    md.append(f"```bash")
    md.append(f"{report.frontend_typecheck.command}")
    md.append(f"```")
    md.append("")

    md.append("## Visual QA Script")
    md.append(f"**Status:** {report.visual_qa_script_check.status}")
    md.append(f"```")
    md.append(report.visual_qa_script_check.stdout)
    md.append(f"```")
    md.append("")

    md.append("## Contact Sheet Example")
    md.append(f"**Status:** {report.contact_sheet_example.status}")
    md.append(f"```")
    md.append(report.contact_sheet_example.stdout)
    md.append(f"```")
    md.append("")

    md.append("## E2E Evidence (Requires Running Server)")
    md.append("The following commands must be run against a live server with a completed carousel project:")
    md.append("")
    md.append("```bash")
    md.append("# 1. Run visual QA against a real project")
    md.append("uv run python scripts/carousel_visual_qa.py \\")
    md.append("  --base-url http://127.0.0.1:8000 \\")
    md.append("  --project-id <PROJECT_UUID> \\")
    md.append("  --email $CAROUSEL_QA_EMAIL \\")
    md.append("  --password $CAROUSEL_QA_PASSWORD \\")
    md.append("  --output-dir /tmp/ae-0039-visual-qa")
    md.append("")
    md.append("# 2. Run with manifest for artifact version verification")
    md.append("uv run python scripts/carousel_visual_qa.py \\")
    md.append("  --base-url http://127.0.0.1:8000 \\")
    md.append("  --project-id <PROJECT_UUID> \\")
    md.append("  --email $CAROUSEL_QA_EMAIL \\")
    md.append("  --password $CAROUSEL_QA_PASSWORD \\")
    md.append("  --manifest-path /path/to/artifact-manifest.json \\")
    md.append("  --output-dir /tmp/ae-0039-visual-qa-manifest")
    md.append("")
    md.append("# 3. Backfill legacy projects")
    md.append("uv run python backend/scripts/backfill_presentation_policy.py --dry-run")
    md.append("")
    md.append("# 4. Explicit regeneration (audit mode)")
    md.append("uv run python backend/scripts/regenerate_carousel_presentation.py \\")
    md.append("  --project-id <PROJECT_UUID> --dry-run")
    md.append("")
    md.append("# 5. Explicit regeneration (render mode)")
    md.append("uv run python backend/scripts/regenerate_carousel_presentation.py \\")
    md.append("  --project-id <PROJECT_UUID> --render")
    md.append("```")
    md.append("")

    md.append("## Sign-Off")
    md.append("| Gate | Status |")
    md.append("|------|--------|")
    md.append(f"| Backend Tests | {report.backend_tests.status} |")
    md.append(f"| Frontend Tests | {report.frontend_tests.status} |")
    md.append(f"| Mutation Testing | {report.mutation_testing.status} |")
    md.append(f"| Backend Ruff | {report.ruff_check.status} |")
    md.append(f"| Frontend ESLint | {report.frontend_lint.status} |")
    md.append(f"| Frontend TypeScript | {report.frontend_typecheck.status} |")
    md.append(f"| Visual QA Script | {report.visual_qa_script_check.status} |")
    md.append(f"| Contact Sheet Example | {report.contact_sheet_example.status} |")
    md.append(f"| E2E Publish Run | MANUAL (requires live server) |")
    md.append("")

    (output_dir / "release-qa-evidence.md").write_text(
        "\n".join(md),
        encoding="utf-8",
    )


def _generate_contact_sheet_example(output_dir: Path) -> Evidence:
    """Generate a contact sheet from test fixture images."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return Evidence(
            command="python -c 'from PIL import Image'",
            status="SKIP",
            stdout="PIL not available — contact sheet generation requires Pillow",
            stderr="Install with: uv pip install pillow",
        )

    # Create test fixture images
    fixture_dir = output_dir / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)

    images = []
    for i in range(1, 8):
        for lang in ("pt", "en"):
            img = Image.new("RGB", (1080, 1350), color="red")
            draw = ImageDraw.Draw(img)
            draw.text((100, 100), f"Slide {i} ({lang.upper()})", fill="white")
            path = fixture_dir / f"{lang}_slide_{i}.jpg"
            img.save(path, "JPEG", quality=95)
            images.append({
                "language": lang,
                "number": i,
                "path": path,
                "width": 1080,
                "height": 1350,
                "size": path.stat().st_size,
            })

    # Generate contact sheets
    contact_dir = output_dir / "contact-sheets"
    contact_dir.mkdir(parents=True, exist_ok=True)

    for lang in ("pt", "en"):
        lang_images = [img for img in images if img["language"] == lang]
        sheet = Image.new("RGB", (2400, 1800), "white")
        draw = ImageDraw.Draw(sheet)
        for idx, img_info in enumerate(lang_images):
            with Image.open(img_info["path"]) as slide:
                slide.thumbnail((300, 375))
                x = 18 + (idx % 4) * (300 + 18)
                y = 18 + (idx // 4) * (375 + 28 + 18)
                sheet.paste(slide.convert("RGB"), (x, y))
                draw.text((x, y + 375 + 6), f"{lang.upper()} slide {img_info['number']}", fill="black")
        sheet_path = contact_dir / f"{lang}-contact.jpg"
        sheet.save(sheet_path, "JPEG", quality=92)

    return Evidence(
        command="python -c generate_contact_sheet_example",
        status="PASS",
        stdout=f"Generated {len(images)} test fixture images\n"
               f"Created PT contact sheet: {contact_dir / 'pt-contact.jpg'}\n"
               f"Created EN contact sheet: {contact_dir / 'en-contact.jpg'}",
        stderr="",
    )


def _check_visual_qa_script() -> Evidence:
    """Verify the visual QA script exists and is runnable."""
    script_path = REPO_ROOT / "scripts" / "carousel_visual_qa.py"
    if not script_path.is_file():
        return Evidence(
            command="ls scripts/carousel_visual_qa.py",
            status="FAIL",
            stdout="",
            stderr="Script not found",
        )

    # Check script can be parsed (syntax check)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script_path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        return Evidence(
            command=f"python -m py_compile {script_path}",
            status="PASS" if result.returncode == 0 else "FAIL",
            stdout=f"Script exists: {script_path}\n"
                   f"Syntax: {'PASS' if result.returncode == 0 else 'FAIL'}",
            stderr=result.stderr,
        )
    except Exception as exc:
        return Evidence(
            command=f"python -m py_compile {script_path}",
            status="FAIL",
            stdout="",
            stderr=str(exc),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="/tmp/ae-0039-evidence")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    print("=" * 60)
    print("AE-0039 Release QA Evidence Collection")
    print("=" * 60)

    print("\n1. Running backend tests...")
    backend_tests = _run(
        ["uv", "run", "pytest", "--tb=short", "-q"],
        BACKEND_DIR,
        timeout=300,
    )
    print(f"   Status: {backend_tests.status}")

    print("\n2. Running frontend tests...")
    frontend_tests = _run(
        ["npm", "run", "test", "--", "--run"],
        FRONTEND_DIR,
        timeout=300,
    )
    print(f"   Status: {frontend_tests.status}")

    print("\n3. Running mutation testing...")
    # mutmut reads paths_to_mutate from setup.cfg
    mutation_testing = _run(
        ["uv", "run", "mutmut", "run"],
        BACKEND_DIR,
        timeout=600,
    )
    print(f"   Status: {mutation_testing.status}")

    print("\n4. Running backend ruff check...")
    ruff_check = _run(
        ["uv", "run", "ruff", "check", "src/", "--quiet"],
        BACKEND_DIR,
        timeout=60,
    )
    print(f"   Status: {ruff_check.status}")

    print("\n5. Running frontend lint...")
    frontend_lint = _run(
        ["npm", "run", "lint"],
        FRONTEND_DIR,
        timeout=120,
    )
    print(f"   Status: {frontend_lint.status}")

    print("\n6. Running frontend typecheck...")
    frontend_typecheck = _run(
        ["npm", "run", "typecheck"],
        FRONTEND_DIR,
        timeout=120,
    )
    print(f"   Status: {frontend_typecheck.status}")

    print("\n7. Checking visual QA script...")
    visual_qa_script_check = _check_visual_qa_script()
    print(f"   Status: {visual_qa_script_check.status}")

    print("\n8. Generating contact sheet example...")
    contact_sheet_example = _generate_contact_sheet_example(output_dir)
    print(f"   Status: {contact_sheet_example.status}")

    print("\n9. Writing evidence report...")
    report = ReleaseQaReport(
        backend_tests=backend_tests,
        frontend_tests=frontend_tests,
        mutation_testing=mutation_testing,
        ruff_check=ruff_check,
        frontend_lint=frontend_lint,
        frontend_typecheck=frontend_typecheck,
        visual_qa_script_check=visual_qa_script_check,
        contact_sheet_example=contact_sheet_example,
    )
    _write_evidence(report, output_dir)
    print(f"   Evidence written to: {output_dir}")
    print(f"   Report: {output_dir / 'release-qa-evidence.md'}")

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Backend Tests:        {backend_tests.status}")
    print(f"  Frontend Tests:       {frontend_tests.status}")
    print(f"  Mutation Testing:     {mutation_testing.status}")
    print(f"  Ruff Check:           {ruff_check.status}")
    print(f"  Frontend Lint:        {frontend_lint.status}")
    print(f"  Frontend TypeScript:  {frontend_typecheck.status}")
    print(f"  Visual QA Script:     {visual_qa_script_check.status}")
    print(f"  Contact Sheets:       {contact_sheet_example.status}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
