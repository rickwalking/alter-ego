"""DeepAgents-compatible sub-agent spec for the carousel pipeline.

DeepAgents expects `CompiledSubAgent = {"name", "description", "runnable"}`
where the runnable's state schema includes a `messages` key — the last
message the runnable emits becomes a `ToolMessage` handed back to the
parent agent.

Our raw `build_graph()` returns a PipelineState graph without a
messages channel. This module wraps it in an outer graph that:

1. Parses a simple JSON request dict from the last user message —
   `{"project_id": "...", "seed_urls": [...]}` — so the parent can
   invoke the subagent with structured args.
2. Runs the inner carousel StateGraph.
3. Emits a summary `AIMessage` describing the outcome, which the
   parent reads as the subagent's reply.

The existing `rag_agent.generate_carousel` tool still works — this
module exists so future DeepAgents integrations (per-turn streaming
into the parent conversation, isolated sub-agent context windows)
have a drop-in `CompiledSubAgent` to register.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Annotated, TypedDict
from uuid import UUID

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from rag_backend.application.services.carousel.graph import (
    CarouselDeps,
    build_graph,
)
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.domain.constants.retry import LANGGRAPH_MAX_ATTEMPTS
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.retry import retry_async

SUBAGENT_NAME = "generate_carousel"
SUBAGENT_DESCRIPTION = (
    "Generate a bilingual Instagram carousel + blog from a topic, audience, "
    "and niche. Researches the web, drafts slides, designs the theme, renders "
    "images, exports PDFs, and writes an Instagram caption plus LinkedIn "
    "posts. Request must include a project_id already created via the "
    "carousel API."
)


class CarouselSubAgentState(TypedDict, total=False):
    """Outer state for the DeepAgents-compatible carousel subagent.

    `messages` is the DeepAgents handshake. The inner pipeline state
    (project, slides_data, etc.) is carried through as well so the
    subagent's checkpointer can resume mid-pipeline.
    """

    messages: Annotated[Sequence[AnyMessage], add_messages]
    project_id: UUID
    seed_urls: list[str]
    output_dir: str
    project: CarouselProject


def _parse_request(messages: Sequence[AnyMessage]) -> dict[str, object]:
    """Extract `{project_id, seed_urls}` from the last HumanMessage.

    Expected payload is a JSON object serialized in the message content.
    Falls back to an empty dict on malformed input — the downstream
    request_node then returns an error message without invoking the
    pipeline.
    """
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            try:
                parsed = json.loads(msg.content if isinstance(msg.content, str) else "")
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                return {}
    return {}


def build_carousel_subagent(
    deps: CarouselDeps,
    *,
    checkpointer: BaseCheckpointSaver[object] | None = None,
    output_base_dir: str = "./output/carousels",
) -> dict[str, object]:
    """Return a CompiledSubAgent-shaped dict for the carousel pipeline.

    Shape matches `deepagents.CompiledSubAgent`: `{name, description, runnable}`.
    """
    inner_graph = build_graph(deps, checkpointer=checkpointer)

    async def request_node(state: CarouselSubAgentState) -> dict[str, object]:
        """Parse the request message, load the project, seed inner state."""
        parsed = _parse_request(state.get("messages", []))
        project_id_raw = parsed.get("project_id")
        if not project_id_raw:
            return {
                "messages": [
                    AIMessage(content=("carousel subagent: missing `project_id` in request"))
                ],
            }
        try:
            project_id = UUID(str(project_id_raw))
        except ValueError:
            return {
                "messages": [
                    AIMessage(content=f"carousel subagent: invalid project_id {project_id_raw!r}")
                ],
            }

        project = await deps.repo.get_project_by_id(project_id)
        if project is None:
            return {
                "messages": [
                    AIMessage(content=f"carousel subagent: project {project_id} not found")
                ],
            }

        seed_urls_raw = parsed.get("seed_urls") or []
        seed_urls = [str(u) for u in seed_urls_raw if isinstance(u, str)]
        output_dir = f"{output_base_dir.rstrip('/')}/{project_id}"
        return {
            "project_id": project_id,
            "seed_urls": seed_urls,
            "output_dir": output_dir,
            "project": project,
        }

    async def run_pipeline_node(state: CarouselSubAgentState) -> dict[str, object]:
        """Delegate to the inner carousel graph."""
        if "project" not in state:
            # request_node already produced an error message.
            return {}
        inner_state: PipelineState = {
            "project_id": state["project_id"],
            "seed_urls": state.get("seed_urls", []),
            "output_dir": state["output_dir"],
            "project": state["project"],
        }
        async for attempt in retry_async(attempts=LANGGRAPH_MAX_ATTEMPTS):
            with attempt:
                final = await inner_graph.ainvoke(inner_state)
        return {"project": final["project"]}

    async def emit_summary_node(state: CarouselSubAgentState) -> dict[str, object]:
        """Produce the AIMessage DeepAgents returns to the parent as a ToolMessage."""
        project = state.get("project")
        if project is None:
            return {}
        summary = (
            f"Carousel project {project.id} finished with status {project.status.value}. "
            f"PT PDF: {project.pdf_path or '(none)'}; EN PDF: {project.pdf_path_en or '(none)'}."
        )
        return {"messages": [AIMessage(content=summary)]}

    outer = StateGraph(CarouselSubAgentState)
    outer.add_node("request", request_node)
    outer.add_node("run", run_pipeline_node)
    outer.add_node("summary", emit_summary_node)
    outer.add_edge(START, "request")
    outer.add_edge("request", "run")
    outer.add_edge("run", "summary")
    outer.add_edge("summary", END)

    return {
        "name": SUBAGENT_NAME,
        "description": SUBAGENT_DESCRIPTION,
        "runnable": outer.compile(checkpointer=checkpointer),
    }
