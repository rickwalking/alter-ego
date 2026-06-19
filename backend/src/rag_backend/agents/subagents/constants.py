"""Constants for the researcher subagent definition (AE-0249)."""

from __future__ import annotations

RESEARCHER_SUBAGENT_NAME = "researcher"
RESEARCHER_SUBAGENT_DESCRIPTION = (
    "Browse a pasted URL or search the web, then synthesize factual sources for "
    "carousel content. Runs in an isolated context with web research tools."
)

# Skill context the researcher READS (markdown only — ADR-0016 skill/tool split).
RESEARCH_PHASE_SKILL_SUBPATH = "phases/research"
SHARED_CRITICAL_RULES_SUBPATH = "_shared/critical-rules.md"

# DeepAgents subagent spec field names (the standard tools/prompt/model surface).
SPEC_FIELD_NAME = "name"
SPEC_FIELD_DESCRIPTION = "description"
SPEC_FIELD_PROMPT = "prompt"
SPEC_FIELD_TOOLS = "tools"
SPEC_FIELD_MODEL = "model"

RESEARCHER_PROMPT_HEADER = (
    "You are the researcher subagent. Use the scrape_url tool to browse any URL "
    "the user provides, search_web to find additional sources, and "
    "search_documents to consult the internal knowledge base. Synthesize the "
    "findings into a concise, cited list of factual sources. If a URL is "
    "unreachable, report it and continue with the remaining sources."
)
RESEARCHER_SKILL_SECTION = "## Research skill"
RESEARCHER_RULES_SECTION = "## Critical rules"

__all__ = [
    "RESEARCHER_PROMPT_HEADER",
    "RESEARCHER_RULES_SECTION",
    "RESEARCHER_SKILL_SECTION",
    "RESEARCHER_SUBAGENT_DESCRIPTION",
    "RESEARCHER_SUBAGENT_NAME",
    "RESEARCH_PHASE_SKILL_SUBPATH",
    "SHARED_CRITICAL_RULES_SUBPATH",
    "SPEC_FIELD_DESCRIPTION",
    "SPEC_FIELD_MODEL",
    "SPEC_FIELD_NAME",
    "SPEC_FIELD_PROMPT",
    "SPEC_FIELD_TOOLS",
]
