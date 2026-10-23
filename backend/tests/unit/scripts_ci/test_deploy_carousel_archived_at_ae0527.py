"""Deploy ordering of the carousel archived_at one-shot.

Scenario: The deploy adds archived_at before the stack comes up and never keeps it down
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DEPLOY = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
COMPOSE = "docker compose -f docker-compose.prod.yml"
PALETTE_STEP = "python -m rag_backend.scripts.palette_timestamptz --apply --verify"
STEP = "python -m rag_backend.scripts.carousel_archived_at --apply --verify"
FINAL_CHECK = 'if [ "$ARCHIVED_AT_EXIT" -ne 0 ]'
ONE_SHOT_EXIT = 'if [ "$ONE_SHOT_FAILED" -ne 0 ]'


def _script() -> str:
    return DEPLOY.read_text(encoding="utf-8")


def _index(text: str, needle: str) -> int:
    position = text.find(needle)
    assert position >= 0, f"deploy.yml is missing: {needle}"
    return position


def test_step_runs_after_the_palette_step_and_before_stack_up() -> None:
    """The one-shot runs on the healthy database, after the palette step."""
    text = _script()
    healthy = _index(text, "pg_isready")
    palette = _index(text, PALETTE_STEP)
    step = _index(text, STEP)
    stack_up = _index(text, f"{COMPOSE} up -d\n")
    assert healthy < palette < step < stack_up


def test_step_uses_the_freshly_built_image_without_app_overlap() -> None:
    """The one-shot runs in a throwaway backend container."""
    text = _script()
    step = _index(text, STEP)
    command = text[text.rfind(COMPOSE, 0, step) : step]
    assert "run --rm --no-deps backend" in command


def test_step_failure_never_keeps_the_stack_down() -> None:
    """A failed one-shot is recorded and the stack still comes up."""
    text = _script()
    step = _index(text, STEP)
    stack_up = _index(text, f"{COMPOSE} up -d\n")
    before = text[text.rfind(COMPOSE, 0, step) - 40 : step]
    assert "set +e" in before
    between = text[step:stack_up]
    assert "ARCHIVED_AT_EXIT=$?" in between
    assert "set -e" in between
    assert "exit 1" not in between


def test_step_failure_fails_the_job_after_the_stack_is_up() -> None:
    """The deploy job fails only once the stack is up again."""
    text = _script()
    stack_up = _index(text, f"{COMPOSE} up -d\n")
    final_check = text.rfind(FINAL_CHECK)
    assert final_check > stack_up
    assert "ONE_SHOT_FAILED=1" in text[final_check : text.find("fi", final_check)]
    single_exit = text.find(ONE_SHOT_EXIT, final_check)
    assert single_exit > final_check
    assert "exit 1" in text[single_exit : text.find("fi", single_exit)]
    assert f"{COMPOSE} down" not in text[final_check:]
