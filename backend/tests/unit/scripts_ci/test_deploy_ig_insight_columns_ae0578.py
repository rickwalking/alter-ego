"""Deploy ordering of the insight columns one-shot and the schema drift check.

Scenario: The deploy adds the insight columns and checks drift without keeping the stack down
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DEPLOY = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
COMPOSE = "docker compose -f docker-compose.prod.yml"
QUEUE_STEP = "python -m rag_backend.scripts.generation_queue_schema --apply --verify"
STEP = "python -m rag_backend.scripts.ig_insight_columns --apply --verify"
DRIFT_STEP = "python -m rag_backend.infrastructure.database.check_drift_cli"
STACK_UP = f"{COMPOSE} up -d\n"
ONE_SHOT_EXIT = 'if [ "$ONE_SHOT_FAILED" -ne 0 ]'


def _script() -> str:
    return DEPLOY.read_text(encoding="utf-8")


def _index(text: str, needle: str) -> int:
    position = text.find(needle)
    assert position >= 0, f"deploy.yml is missing: {needle}"
    return position


def _lines_before(text: str, position: int, count: int) -> list[str]:
    line_start = text.rfind("\n", 0, position)
    return [line.strip() for line in text[:line_start].splitlines()[-count:]]


def _fails_the_job_at_the_end(text: str, exit_var: str) -> None:
    stack_up = _index(text, STACK_UP)
    final_check = text.rfind(f'if [ "${exit_var}" -ne 0 ]')
    assert final_check > stack_up
    assert "ONE_SHOT_FAILED=1" in text[final_check : text.find("fi", final_check)]
    single_exit = text.find(ONE_SHOT_EXIT, final_check)
    assert single_exit > final_check
    assert "exit 1" in text[single_exit : text.find("fi", single_exit)]
    assert f"{COMPOSE} down" not in text[final_check:]


def test_one_shot_runs_after_the_queue_schema_and_before_stack_up() -> None:
    """The one-shot runs on the database before the app starts."""
    text = _script()
    assert _index(text, QUEUE_STEP) < _index(text, STEP) < _index(text, STACK_UP)


def test_one_shot_uses_a_throwaway_container_and_never_keeps_the_stack_down() -> None:
    """A failed one-shot is recorded and the stack still comes up."""
    text = _script()
    step = _index(text, STEP)
    compose = text.rfind(COMPOSE, 0, step)
    assert "run --rm --no-deps backend" in text[compose:step]
    assert _lines_before(text, compose, 1) == ["set +e"]
    between = text[step : _index(text, STACK_UP)]
    assert "IG_INSIGHT_COLUMNS_EXIT=$?" in between
    assert "set -e" in between
    assert "exit 1" not in between


def test_one_shot_failure_fails_the_job_after_the_stack_is_up() -> None:
    """The deploy job fails only once the stack is up again."""
    _fails_the_job_at_the_end(_script(), "IG_INSIGHT_COLUMNS_EXIT")


def test_drift_check_runs_in_the_running_backend_after_stack_up() -> None:
    """The drift check reads the live schema once create_all has run."""
    text = _script()
    drift = _index(text, DRIFT_STEP)
    assert _index(text, STACK_UP) < drift
    compose = text.rfind(COMPOSE, 0, drift)
    assert "exec -T backend" in text[compose:drift]
    assert _lines_before(text, compose, 1) == ["set +e"]


def test_drift_check_retries_and_never_exits_inside_the_loop() -> None:
    """A slow backend start is retried; the loop itself never fails the deploy."""
    text = _script()
    drift = _index(text, DRIFT_STEP)
    loop = text.rfind("for attempt in", 0, drift)
    done = text.find("done\n", drift)
    assert 0 <= loop < drift < done
    body = text[loop:done]
    assert "SCHEMA_DRIFT_EXIT=$?" in body
    assert "break" in body
    assert "exit 1" not in body


def test_drift_failure_fails_the_job_at_the_end() -> None:
    """Drift is reported with the stack up and fails the job at the end."""
    _fails_the_job_at_the_end(_script(), "SCHEMA_DRIFT_EXIT")
