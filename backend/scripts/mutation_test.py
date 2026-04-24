#!/usr/bin/env python3
"""Targeted mutation testing for carousel pipeline changes.

This script manually applies mutations to the two files we modified
(carousel_agent.py and graph.py) and runs the relevant unit tests
to verify that our tests kill the mutants.

Run with: uv run python scripts/mutation_test.py
"""

import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
SRC_DIR = BACKEND_DIR / "src"
TEST_FILE = BACKEND_DIR / "tests" / "unit" / "application" / "test_carousel_graph.py"

MUTATIONS = [
    # --- carousel_agent.py mutations ---
    {
        "file": "rag_backend/application/services/carousel_agent.py",
        "name": "stream_checkpoint: skip check (config is None)",
        "find": "        if config is not None:\n            try:\n                snapshot = await graph.aget_state(config)\n                has_checkpoint = snapshot is not None and bool(snapshot.values)\n            except Exception:\n                has_checkpoint = False",
        "replace": "        if config is None:\n            try:\n                snapshot = await graph.aget_state(config)\n                has_checkpoint = snapshot is not None and bool(snapshot.values)\n            except Exception:\n                has_checkpoint = False",
        "tests_should_kill": ["test_stream_pipeline_resumes_from_checkpoint"],
    },
    {
        "file": "rag_backend/application/services/carousel_agent.py",
        "name": "stream_checkpoint: force has_checkpoint=True always",
        "find": "        has_checkpoint = False",
        "replace": "        has_checkpoint = True",
        "tests_should_kill": ["test_stream_pipeline_yields_progress_events"],
    },
    {
        "file": "rag_backend/application/services/carousel_agent.py",
        "name": "stream_checkpoint: swap ternary (always resume)",
        "find": "            stream_input = None if has_checkpoint else initial_state",
        "replace": "            stream_input = initial_state if has_checkpoint else None",
        "tests_should_kill": ["test_stream_pipeline_resumes_from_checkpoint"],
    },
    # --- graph.py mutations ---
    {
        "file": "rag_backend/application/services/carousel/graph.py",
        "name": "persist_slides: empty existing lookup",
        "find": "        existing_by_number = {s.slide_number: s for s in existing_slides}",
        "replace": "        existing_by_number = {}",
        "tests_should_kill": ["test_persist_slides_is_idempotent_on_resume"],
    },
    {
        "file": "rag_backend/application/services/carousel/graph.py",
        "name": "persist_slides: invert existing check",
        "find": "            if existing:",
        "replace": "            if not existing:",
        "tests_should_kill": ["test_persist_slides_is_idempotent_on_resume"],
    },
    {
        "file": "rag_backend/application/services/carousel/graph.py",
        "name": "persist_slides: skip update_slide call",
        "find": "                await deps.repo.update_slide(updated)",
        "replace": "                pass  # skipped update",
        "tests_should_kill": ["test_persist_slides_is_idempotent_on_resume"],
    },
]


def apply_mutation(source: str, find: str, replace: str) -> str:
    if find not in source:
        raise ValueError("Could not find mutation target in source")
    return source.replace(find, replace, 1)


def run_tests(test_filter: list[str]) -> tuple[int, str]:
    """Run pytest with the given test filter. Returns (exit_code, output)."""
    cmd = [
        "uv",
        "run",
        "pytest",
        str(TEST_FILE),
        "-v",
        "--tb=short",
        "-x",
    ]
    for t in test_filter:
        cmd.extend(["-k", t])

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
    print("Targeted Mutation Tests — Carousel Pipeline")
    print("=" * 60)

    for mutation in MUTATIONS:
        file_path = SRC_DIR / mutation["file"]
        original = file_path.read_text()

        try:
            mutated = apply_mutation(original, mutation["find"], mutation["replace"])
        except ValueError as e:
            print(f"\n🤔 {mutation['name']}")
            print(f"   Could not apply mutation: {e}")
            errors += 1
            continue

        # Write mutant
        file_path.write_text(mutated)

        try:
            exit_code, output = run_tests(mutation["tests_should_kill"])
            if exit_code != 0:
                print(f"\n🎉 {mutation['name']}")
                print("   KILLED — tests failed as expected")
                killed += 1
            else:
                print(f"\n🫥 {mutation['name']}")
                print("   SURVIVED — tests passed despite mutation")
                print(f"   Output: {output[:300]}...")
                survived += 1
        except Exception as e:
            print(f"\n🙁 {mutation['name']}")
            print(f"   ERROR running tests: {e}")
            errors += 1
        finally:
            # Restore original
            file_path.write_text(original)

    print("\n" + "=" * 60)
    print(f"Results: {killed} killed, {survived} survived, {errors} errors")
    print("=" * 60)

    if survived > 0 or errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
