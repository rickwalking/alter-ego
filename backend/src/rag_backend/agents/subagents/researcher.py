"""The ``researcher`` subagent — URL navigation for carousel creation (AE-0249).

A true, isolated-context DeepAgents subagent (ADR-0015) granted the web-research
@tool adapters (``scrape_url`` / ``search_web``) plus ``search_documents``. It is
defined with the standard DeepAgents ``tools`` / ``prompt`` / ``model`` fields and
reads the ``phases/research`` + ``_shared/critical-rules`` skill context.

Skill markdown is *content* the agent reads (ADR-0016 skill/tool split); the tool
adapters delegate to the ``application`` research service through a Protocol, so
this module imports no ``application`` and no infrastructure beyond logging.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from rag_backend.agents.subagents.constants import (
    RESEARCH_PHASE_SKILL_SUBPATH,
    RESEARCHER_PROMPT_HEADER,
    RESEARCHER_RULES_SECTION,
    RESEARCHER_SKILL_SECTION,
    RESEARCHER_SUBAGENT_DESCRIPTION,
    RESEARCHER_SUBAGENT_NAME,
    SHARED_CRITICAL_RULES_SUBPATH,
    SPEC_FIELD_DESCRIPTION,
    SPEC_FIELD_MODEL,
    SPEC_FIELD_NAME,
    SPEC_FIELD_PROMPT,
    SPEC_FIELD_TOOLS,
)
from rag_backend.agents.tools import build_scrape_url_tool, build_search_web_tool
from rag_backend.domain.constants.runtime_skills import (
    carousel_pipeline_root,
    read_runtime_shared_markdown,
    read_runtime_skill_markdown,
)
from rag_backend.domain.protocols import ResearchTool
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


@dataclass(frozen=True)
class ResearcherSubagentConfig:
    """Typed inputs for :func:`build_researcher_subagent` (≤3-arg rule)."""

    research: ResearchTool
    search_documents: BaseTool
    model: BaseChatModel | None = None


def _read_section(loader: Callable[[str], str], logical_path: str) -> str:
    """Read a skill markdown section, tolerating an absent runtime tree."""
    try:
        return loader(logical_path)
    except (FileNotFoundError, OSError) as exc:
        logger.warning("researcher_skill_missing", path=logical_path, error=str(exc))
        return ""


def _load_skill_context() -> str:
    """Assemble the research skill + critical-rules context (content only)."""
    root = carousel_pipeline_root()
    skill = _read_section(
        read_runtime_skill_markdown, f"{root}/{RESEARCH_PHASE_SKILL_SUBPATH}"
    )
    rules = _read_section(
        read_runtime_shared_markdown, f"{root}/{SHARED_CRITICAL_RULES_SUBPATH}"
    )
    sections = [RESEARCHER_PROMPT_HEADER]
    if skill:
        sections.extend([RESEARCHER_SKILL_SECTION, skill])
    if rules:
        sections.extend([RESEARCHER_RULES_SECTION, rules])
    return "\n\n".join(sections)


def build_researcher_subagent(
    config: ResearcherSubagentConfig,
) -> dict[str, object]:
    """Return a DeepAgents subagent spec for the ``researcher`` subagent.

    The spec uses the standard DeepAgents ``tools`` / ``prompt`` / ``model``
    fields. Tools are the two thin research @tool adapters plus the shared
    ``search_documents`` tool; the prompt embeds the research skill context.
    """
    tools: list[BaseTool] = [
        build_scrape_url_tool(config.research),
        build_search_web_tool(config.research),
        config.search_documents,
    ]
    spec: dict[str, object] = {
        SPEC_FIELD_NAME: RESEARCHER_SUBAGENT_NAME,
        SPEC_FIELD_DESCRIPTION: RESEARCHER_SUBAGENT_DESCRIPTION,
        SPEC_FIELD_PROMPT: _load_skill_context(),
        SPEC_FIELD_TOOLS: tools,
    }
    if config.model is not None:
        spec[SPEC_FIELD_MODEL] = config.model
    return spec


__all__ = [
    "RESEARCHER_SUBAGENT_NAME",
    "ResearcherSubagentConfig",
    "build_researcher_subagent",
]
