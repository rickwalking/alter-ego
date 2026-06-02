#!/usr/bin/env python3
"""Targeted mutation testing for carousel editorial workflow modules.

Run with: uv run python scripts/mutation_test.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
SRC_DIR = BACKEND_DIR / "src"
TEST_FILE = (
    BACKEND_DIR / "tests" / "unit" / "agents" / "test_carousel_workflow_phases.py"
)

MUTATIONS = [
    {
        "file": "rag_backend/application/services/carousel/workflow_sse_hub.py",
        "name": "SSE hub: skip keepalive marker on idle timeout",
        "find": "                    yield {SSE_EVENT_KEY: SSE_EVENT_KEEPALIVE}",
        "replace": "                    continue",
        "tests_should_kill": [
            "test_mutation_keepalive_marker_is_distinct_from_progress"
        ],
        "test_file": "tests/unit/application/test_mutation_sse_workflow.py",
    },
    {
        "file": "rag_backend/application/services/carousel/editorial_workflow_support.py",
        "name": "SSE publish: drop review_required at human gate",
        "find": "    if phase_status == PHASE_STATUS_AWAITING_HUMAN:",
        "replace": "    if phase_status == PHASE_STATUS_FAILED:",
        "tests_should_kill": ["test_mutation_review_required_emitted_at_human_gate"],
        "test_file": "tests/unit/application/test_mutation_sse_workflow.py",
    },
    {
        "file": "rag_backend/agents/carousel_workflow_nodes.py",
        "name": "review_updates: approve returns awaiting_human",
        "find": '        return {"phase_status": PHASE_STATUS_APPROVED}',
        "replace": '        return {"phase_status": PHASE_STATUS_AWAITING_HUMAN}',
        "tests_should_kill": ["test_approve_returns_approved_status"],
    },
    {
        "file": "rag_backend/agents/carousel_workflow_graph.py",
        "name": "route_after_final_review: ignore send-back target",
        "find": "        return target",
        "replace": "        return _ROUTE_RETRY",
        "tests_should_kill": ["test_route_after_final_review_send_back_to_content"],
    },
    {
        "file": "rag_backend/application/services/carousel/refinement_service.py",
        "name": "re_render: skip bilingual export",
        "find": "        await self._phase6_bilingual_export(",
        "replace": "        pass  # skipped export\n        # await self._phase6_bilingual_export(",
        "tests_should_kill": ["test_re_render_writes_pdf_and_bumps_updated_at"],
    },
]


def apply_mutation(source: str, find: str, replace: str) -> str:
    if find not in source:
        raise ValueError("Could not find mutation target in source")
    return source.replace(find, replace, 1)


def run_tests(
    test_filter: list[str],
    extra_test_path: Path | None = None,
    test_file: Path | None = None,
) -> tuple[int, str]:
    """Run pytest with the given test filter. Returns (exit_code, output)."""
    target = test_file or TEST_FILE
    cmd = [
        "uv",
        "run",
        "pytest",
        str(target),
        "-v",
        "--tb=short",
        "-x",
    ]
    if extra_test_path is not None:
        cmd.append(str(extra_test_path))
    for test_name in test_filter:
        cmd.extend(["-k", test_name])

    result = subprocess.run(
        cmd,
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode, result.stdout + result.stderr


def main() -> int:
    killed = 0
    survived = 0
    errors = 0

    print("=" * 60)
    print("Targeted Mutation Tests — Carousel Editorial Workflow")
    print("=" * 60)

    re_render_tests = (
        BACKEND_DIR / "tests" / "unit" / "application" / "test_re_render_slides.py"
    )

    for mutation in MUTATIONS:
        file_path = SRC_DIR / mutation["file"]
        original = file_path.read_text()

        try:
            mutated = apply_mutation(original, mutation["find"], mutation["replace"])
        except ValueError as exc:
            print(f"\n🤔 {mutation['name']}")
            print(f"   Could not apply mutation: {exc}")
            errors += 1
            continue

        file_path.write_text(mutated)

        extra = (
            re_render_tests
            if mutation["file"].endswith("refinement_service.py")
            else None
        )
        mutation_test_file = BACKEND_DIR / mutation.get(
            "test_file",
            "tests/unit/agents/test_carousel_workflow_phases.py",
        )

        try:
            exit_code, output = run_tests(
                mutation["tests_should_kill"],
                extra,
                mutation_test_file,
            )
            if exit_code != 0:
                print(f"\n🎉 {mutation['name']}")
                print("   KILLED — tests failed as expected")
                killed += 1
            else:
                print(f"\n🫥 {mutation['name']}")
                print("   SURVIVED — tests passed despite mutation")
                print(f"   Output: {output[:300]}...")
                survived += 1
        except Exception as exc:
            print(f"\n🙁 {mutation['name']}")
            print(f"   ERROR running tests: {exc}")
            errors += 1
        finally:
            file_path.write_text(original)

    print("\n" + "=" * 60)
    print(f"Results: {killed} killed, {survived} survived, {errors} errors")
    print("=" * 60)

    if survived > 0 or errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
