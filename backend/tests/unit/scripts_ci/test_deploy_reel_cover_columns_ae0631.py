"""Deploy ordering of the reel cover columns one-shot.

Gherkin: tests/features/reel_cover_columns_oneshot_ae0631.feature
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DEPLOY = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
COMPOSE = "docker compose -f docker-compose.prod.yml"
PREVIOUS_STEP = "python -m rag_backend.scripts.token_version_column --apply --verify"
STEP = "python -m rag_backend.scripts.reel_cover_columns --apply --verify"
DRIFT_STEP = "python -m rag_backend.infrastructure.database.check_drift_cli"
STACK_UP = f"{COMPOSE} up -d\n"
EXIT_VAR = "REEL_COVER_COLUMNS_EXIT"
ONE_SHOT_EXIT = 'if [ "$ONE_SHOT_FAILED" -ne 0 ]'


def _script() -> str:
    return DEPLOY.read_text(encoding="utf-8")


def _index(text: str, needle: str) -> int:
    position = text.find(needle)
    assert position >= 0, f"deploy.yml is missing: {needle}"
    return position


# Scenario: The deploy adds the reel cover columns without keeping the stack down
def test_the_one_shot_runs_after_token_version_and_before_stack_up() -> None:
    text = _script()
    step = _index(text, STEP)
    assert _index(text, PREVIOUS_STEP) < step < _index(text, STACK_UP)
    assert step < _index(text, DRIFT_STEP)


# Scenario: The deploy adds the reel cover columns without keeping the stack down
def test_the_one_shot_runs_in_a_throwaway_container_without_exiting() -> None:
    text = _script()
    step = _index(text, STEP)
    compose = text.rfind(COMPOSE, 0, step)
    assert "run --rm --no-deps backend" in text[compose:step]
    before = text[: text.rfind("\n", 0, compose)].splitlines()[-1].strip()
    assert before == "set +e"
    between = text[step : _index(text, STACK_UP)]
    assert f"{EXIT_VAR}=$?" in between
    assert "set -e" in between
    assert "exit 1" not in between


# Scenario: The deploy adds the reel cover columns without keeping the stack down
def test_a_one_shot_failure_fails_the_job_after_the_stack_is_up() -> None:
    text = _script()
    final_check = text.rfind(f'if [ "${EXIT_VAR}" -ne 0 ]')
    assert final_check > _index(text, STACK_UP)
    block = text[final_check : text.find("fi", final_check)]
    assert "ONE_SHOT_FAILED=1" in block
    assert "reel_cover_columns --apply --verify' on the droplet" in block
    single_exit = text.find(ONE_SHOT_EXIT, final_check)
    assert single_exit > final_check
    assert "exit 1" in text[single_exit : text.find("fi", single_exit)]
    assert f"{COMPOSE} down" not in text[final_check:]
