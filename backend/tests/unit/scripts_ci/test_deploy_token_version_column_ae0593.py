"""Deploy ordering of the ``users.token_version`` one-shot.

Scenarios: ``tests/features/logout_other_sessions_ae0593.feature``.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DEPLOY = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
COMPOSE = "docker compose -f docker-compose.prod.yml"
PREVIOUS_STEP = (
    "python -m rag_backend.scripts.must_change_password_column --apply --verify"
)
STEP = "python -m rag_backend.scripts.token_version_column --apply --verify"
DRIFT_STEP = "python -m rag_backend.infrastructure.database.check_drift_cli"
STACK_UP = f"{COMPOSE} up -d\n"
EXIT_VAR = "TOKEN_VERSION_EXIT"
ONE_SHOT_EXIT = 'if [ "$ONE_SHOT_FAILED" -ne 0 ]'
RETRY_GUARD = f'if [ "${EXIT_VAR}" -ne 0 ]; then'
RETRY_EXEC = f"{COMPOSE} exec -T backend \\\n                {STEP}"


def _script() -> str:
    return DEPLOY.read_text(encoding="utf-8")


def _index(text: str, needle: str) -> int:
    position = text.find(needle)
    assert position >= 0, f"deploy.yml is missing: {needle}"
    return position


# Scenario: The deploy runs the token version one-shot before the stack comes up
def test_the_one_shot_runs_after_the_flag_step_and_before_stack_up() -> None:
    """The column exists before the app (and the drift check) starts."""
    text = _script()
    step = _index(text, STEP)
    assert _index(text, PREVIOUS_STEP) < step < _index(text, STACK_UP)
    assert step < _index(text, DRIFT_STEP)


# Scenario: The deploy runs the token version one-shot before the stack comes up
def test_the_one_shot_runs_in_a_throwaway_container_without_exiting() -> None:
    """A failed run is recorded and the stack still comes up."""
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


# Scenario: The deploy runs the token version one-shot before the stack comes up
def test_a_one_shot_failure_fails_the_job_after_the_stack_is_up() -> None:
    """The job fails at the very end, never taking the stack down."""
    text = _script()
    final_check = text.rfind(f'if [ "${EXIT_VAR}" -ne 0 ]')
    assert final_check > _index(text, STACK_UP)
    assert "ONE_SHOT_FAILED=1" in text[final_check : text.find("fi", final_check)]
    single_exit = text.find(ONE_SHOT_EXIT, final_check)
    assert single_exit > final_check
    assert "exit 1" in text[single_exit : text.find("fi", single_exit)]
    assert f"{COMPOSE} down" not in text[final_check:]


def _retry_block(text: str) -> str:
    """The guarded in-stack retry, from its ``if`` to its ``fi``."""
    guard = text.find(RETRY_GUARD, _index(text, STACK_UP))
    assert guard >= 0, "deploy.yml has no in-stack retry of the token version one-shot"
    return text[guard : text.find("\n            fi\n", guard)]


# Scenario: The deploy retries a failed token version one-shot in the running backend
def test_a_failed_one_shot_is_retried_once_after_stack_up() -> None:
    """The retry runs only after a failure, in the running backend, before drift."""
    text = _script()
    block = _retry_block(text)
    retry = text.find(RETRY_EXEC)
    assert _index(text, STACK_UP) < retry < _index(text, DRIFT_STEP)
    assert RETRY_EXEC in block
    assert block.count(STEP) == 1
    assert "set +e" in block
    assert f"{EXIT_VAR}=$?" in block
    assert "exit 1" not in block


# Scenario: The deploy retries a failed token version one-shot in the running backend
def test_the_retry_result_is_what_the_final_check_reads() -> None:
    """A successful retry clears the failure; a failed one still fails the job."""
    text = _script()
    retry = text.find(RETRY_EXEC)
    final_check = text.rfind(f'if [ "${EXIT_VAR}" -ne 0 ]')
    assert retry < final_check
    between = text[retry:final_check]
    assert between.count(f"{EXIT_VAR}=") == 1
    assert (
        "token_version_column --apply --verify' on the droplet"
        in text[final_check : text.find("fi", final_check)]
    )
