"""Prompt template registry with lazy loading and caching.

Usage:
    from rag_backend.agents.prompts.registry import render_prompt, get_system_prompt

    # Render a parameterized prompt
    prompt_text, model_cfg = render_prompt(
        "carousel", "title_prompt",
        variables={"topic": "AI", "audience": "devs"},
        version="v1",
    )

    # Load a system prompt markdown file
    system_prompt = get_system_prompt("rag", version="v1")
"""

from functools import lru_cache
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

PROMPTS_DIR = Path(__file__).parent

_jinja_env = Environment(
    loader=FileSystemLoader(PROMPTS_DIR),
    autoescape=False,  # noqa: S701 — prompts are plain text, not HTML  # nosec B701
)


_ERR_PROMPT_NOT_FOUND = "Prompt not found: {}"


class PromptNotFoundError(LookupError):
    """Raised when a requested prompt template does not exist."""


@lru_cache(maxsize=128)
def _load_prompt_config(domain: str, name: str, version: str) -> dict:
    """Load and cache a prompt configuration file.

    Args:
        domain: Prompt domain (e.g., "carousel", "rag", "refinement").
        name: Prompt name (e.g., "title_prompt", "system").
        version: Prompt version (e.g., "v1", "v2").

    Returns:
        Parsed YAML configuration dictionary.

    Raises:
        PromptNotFoundError: If the prompt file does not exist.
    """
    path = PROMPTS_DIR / domain / version / f"{name}.yaml"
    if not path.exists():
        raise PromptNotFoundError(_ERR_PROMPT_NOT_FOUND.format(path))
    with open(path) as f:
        return yaml.safe_load(f)


def render_prompt(
    domain: str,
    name: str,
    variables: dict[str, object],
    *,
    version: str = "v1",
) -> tuple[str, dict[str, object]]:
    """Render a prompt template with Jinja2 variables.

    Args:
        domain: Prompt domain folder name.
        name: Prompt file name (without extension).
        variables: Dictionary of Jinja2 template variables.
        version: Prompt version folder (default: "v1").

    Returns:
        Tuple of (rendered_prompt_text, model_config_dict).

    Raises:
        PromptNotFoundError: If the prompt template does not exist.
    """
    config = _load_prompt_config(domain, name, version)
    template = _jinja_env.from_string(config["template"])
    rendered = template.render(**variables)
    return rendered, config.get("model", {})


_ERR_SYSTEM_PROMPT_NOT_FOUND = "System prompt not found: {}"


def get_system_prompt(
    agent: str,
    *,
    version: str = "v1",
) -> str:
    """Load a system prompt markdown file.

    Args:
        agent: Agent name folder (e.g., "rag", "carousel").
        version: Prompt version folder (default: "v1").

    Returns:
        Contents of the system.md file.

    Raises:
        PromptNotFoundError: If the system prompt file does not exist.
    """
    path = PROMPTS_DIR / agent / version / "system.md"
    if not path.exists():
        raise PromptNotFoundError(_ERR_SYSTEM_PROMPT_NOT_FOUND.format(path))
    with open(path) as f:
        return f.read()
