"""DeepAgents-compatible editorial carousel subagent (CP-005/CP-026)."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Sequence
from typing import Annotated

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from rag_backend.application.services.carousel.phase_subagents import (
    SUBAGENT_RESEARCH_SYNTHESIZER,
    build_phase_subagent_specs,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)

EDITORIAL_SUBAGENT_NAME = "carousel_editorial_workflow"
EDITORIAL_SUBAGENT_DESCRIPTION = (
    "Start or resume the unified editorial carousel workflow with human review "
    "gates. Request JSON must include project_id and optional workflow action."
)

WorkflowStartFn = Callable[
    [str, dict[str, object]],
    Awaitable[CarouselWorkflowState],
]


class EditorialSubAgentState(dict):
    """Minimal state for editorial subagent handshake."""


def _parse_request(messages: Sequence[AnyMessage]) -> dict[str, object]:
    for msg in reversed(messages):
        if not isinstance(msg, HumanMessage):
            continue
        content = msg.content if isinstance(msg.content, str) else ""
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def build_editorial_carousel_subagent(
    start_workflow: WorkflowStartFn,
) -> dict[str, object]:
    """Return CompiledSubAgent spec for editorial carousel workflow."""

    class _State(dict):
        messages: Annotated[list[AnyMessage], add_messages]

    async def request_node(state: dict[str, object]) -> dict[str, object]:
        parsed = _parse_request(state.get("messages", []))
        project_id = str(parsed.get("project_id", "")).strip()
        if not project_id:
            return {
                "messages": [
                    AIMessage(
                        content="editorial subagent: missing project_id in request"
                    )
                ],
            }
        payload = {
            "topic": str(parsed.get("topic", "")),
            "audience": str(parsed.get("audience", "")),
            "brief": str(parsed.get("brief", parsed.get("topic", ""))),
            "sources": parsed.get("sources", []),
        }
        workflow_state = await start_workflow(project_id, payload)
        phase = str(workflow_state.get("current_phase", ""))
        status = str(workflow_state.get("phase_status", ""))
        summary = (
            f"Editorial workflow active for project {project_id}.\n"
            f"Phase: {phase}\n"
            f"Status: {status}\n"
            f"Subagents: {', '.join(spec['name'] for spec in build_phase_subagent_specs())}"
        )
        return {"messages": [AIMessage(content=summary)]}

    graph = StateGraph(dict)
    graph.add_node("request", request_node)
    graph.add_edge(START, "request")
    graph.add_edge("request", END)

    phase_specs = build_phase_subagent_specs()
    return {
        "name": EDITORIAL_SUBAGENT_NAME,
        "description": EDITORIAL_SUBAGENT_DESCRIPTION,
        "prompt": phase_specs[0]["prompt"] if phase_specs else "",
        "runnable": graph.compile(),
    }


__all__ = [
    "EDITORIAL_SUBAGENT_DESCRIPTION",
    "EDITORIAL_SUBAGENT_NAME",
    "SUBAGENT_RESEARCH_SYNTHESIZER",
    "WorkflowStartFn",
    "build_editorial_carousel_subagent",
]
