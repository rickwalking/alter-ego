"""Deploy ordering of the carousel phase index one-shot (Pedro's decision).

Feature: backend/tests/features/carousel_generation_load_ae0520.feature
Scenario: The deploy runs the phase index after the palette step and never keeps the stack down
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DEPLOY = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
COMPOSE = "docker compose -f docker-compose.prod.yml"
PALETTE = "python -m rag_backend.scripts.palette_timestamptz --apply --verify"
STEP = "python -m rag_backend.scripts.carousel_phase_index --apply --verify"
FINAL_CHECK = 'if [ "$PHASE_INDEX_EXIT" -ne 0 ]'


def _script() -> str:
    return DEPLOY.read_text(encoding="utf-8")


def _index(text: str, needle: str) -> int:
    position = text.find(needle)
    assert position >= 0, f"deploy.yml is missing: {needle}"
    return position


def test_step_runs_after_the_palette_step_and_before_stack_up() -> None:
    text = _script()
    palette = _index(text, PALETTE)
    step = _index(text, STEP)
    stack_up = _index(text, f"{COMPOSE} up -d\n")
    assert palette < step < stack_up


def test_step_uses_the_freshly_built_image_without_app_overlap() -> None:
    text = _script()
    step = _index(text, STEP)
    command = text[text.rfind(COMPOSE, 0, step) : step]
    assert "run --rm --no-deps backend" in command


def test_step_failure_never_keeps_the_stack_down() -> None:
    text = _script()
    step = _index(text, STEP)
    stack_up = _index(text, f"{COMPOSE} up -d\n")
    before = text[text.rfind(COMPOSE, 0, step) - 40 : step]
    assert "set +e" in before
    between = text[step:stack_up]
    assert "PHASE_INDEX_EXIT=$?" in between
    assert "set -e" in between
    assert "exit 1" not in between


def test_step_failure_fails_the_job_after_the_stack_is_up() -> None:
    text = _script()
    stack_up = _index(text, f"{COMPOSE} up -d\n")
    final_check = text.rfind(FINAL_CHECK)
    assert final_check > stack_up
    assert "exit 1" in text[final_check : text.find("fi", final_check)]
    assert f"{COMPOSE} down" not in text[final_check:]
