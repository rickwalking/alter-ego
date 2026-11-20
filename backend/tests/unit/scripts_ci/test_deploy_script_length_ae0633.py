"""The SSH deploy script stays under GitHub's expression length cap.

The script reads ``${{ secrets.* }}``, so GitHub evaluates the whole script as
one expression and refuses the workflow file once it passes 21000 characters:
no job runs and nothing deploys (2026-11-20, d6a8c2a22).
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
DEPLOY = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
STEP_NAME = "Deploy to DigitalOcean via SSH"
GITHUB_EXPRESSION_MAX = 21000


def _script() -> str:
    workflow = yaml.safe_load(DEPLOY.read_text(encoding="utf-8"))
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            if step.get("name") == STEP_NAME:
                return str(step["with"]["script"])
    raise AssertionError(f"deploy.yml has no step named {STEP_NAME!r}")


def test_the_ssh_script_fits_githubs_expression_cap() -> None:
    length = len(_script())
    assert length < GITHUB_EXPRESSION_MAX, (
        f"deploy script is {length} characters; GitHub rejects the workflow at "
        f"{GITHUB_EXPRESSION_MAX}. Move notes out of the script or move steps into "
        "a scripts/deploy/*.sh file."
    )


def test_the_cap_check_fires_on_an_oversized_script() -> None:
    oversized = "x" * GITHUB_EXPRESSION_MAX
    assert not len(oversized) < GITHUB_EXPRESSION_MAX
