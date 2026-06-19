"""DeepAgents subagent specs owned by the agents package (AE-0249).

Only true, isolated-context subagents live here. Deterministic carousel phases
(outline, content, export, DB sync, persona gate) stay raw LangGraph nodes per
ADR-007 and are intentionally absent from this package.
"""

from rag_backend.agents.subagents.researcher import (
    RESEARCHER_SUBAGENT_NAME,
    ResearcherSubagentConfig,
    build_researcher_subagent,
)

__all__ = [
    "RESEARCHER_SUBAGENT_NAME",
    "ResearcherSubagentConfig",
    "build_researcher_subagent",
]
