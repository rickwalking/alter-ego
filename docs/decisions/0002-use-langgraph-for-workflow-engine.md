# ADR-002: Use LangGraph for Workflow Engine

## Status

Accepted

## Context

The current carousel generation is a monolithic pipeline with no pause/resume capability. The pivot requires a 7-phase carousel workflow and a 4-state blog post editorial workflow, both with human approval gates. We need:
1. Stateful, long-running workflows that survive server restarts
2. Human-in-the-loop interrupts at arbitrary points
3. Parallel agent execution (research, drafting, image generation)
4. State persistence and audit trails

## Decision

Use **LangGraph** (built on LangChain) as our workflow orchestration engine, with `PostgresSaver` for checkpoint persistence.

## Decision Drivers

- Must survive server restarts without losing progress
- Must support synchronous human interrupts (approval gates)
- Must execute AI agents in parallel where possible
- Must provide complete audit trail of workflow state changes
- Must integrate with existing LangChain ecosystem (we already use LangChain)

## Considered Options

### Option 1: Custom State Machine with FastAPI Background Tasks

- **Good:** Full control, no external dependency
- **Bad:** Rebuilding checkpointing, interruption, and parallelization from scratch is error-prone and time-consuming
- **Verdict:** Rejected — violates "don't roll your own workflow engine"

### Option 2: Temporal.io

- **Good:** Production-grade, built for durable workflows, excellent observability
- **Bad:** New ecosystem to learn, additional infrastructure (Temporal server), overkill for our current scale
- **Verdict:** Rejected — too heavy for current needs; reconsider if we scale beyond 10k workflows/day

### Option 3: LangGraph

- **Good:**
  - Built-in checkpointing via `PostgresSaver`
  - Native `interrupt()` for human-in-the-loop
  - Subagent pattern for parallel execution
  - Part of existing LangChain ecosystem
  - Fast iteration cycle (LangChain team ships weekly)
  - Strong community and documentation
- **Bad:**
  - Relatively new (v1.0 in 2025); some APIs may change
  - Less mature than Temporal for pure workflow orchestration
  - Requires careful handling of non-deterministic control flow
- **Verdict:** Accepted — best fit for AI-native workflows with human gates

### Option 4: Prefect / Dagster

- **Good:** Mature data pipeline orchestrators
- **Bad:** Designed for data engineering, not AI agent workflows with human interrupts
- **Verdict:** Rejected — wrong abstraction for our use case

## Consequences

**Good:**
- Checkpointing ensures no progress lost on restarts
- Human interrupts feel natural — just pause the graph, wait for input, resume
- Subagents enable parallel research and content drafting
- Event stream from graph execution feeds our audit log

**Bad:**
- Team must learn LangGraph concepts (nodes, edges, state, checkpoints)
- Need to be careful with non-deterministic edges (use conditional edges properly)
- Must avoid bare `try/except` around `interrupt()` calls
- DeltaChannel (LangGraph 1.2+) should be adopted to prevent O(N²) checkpoint growth

## Implementation Notes

```python
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph

# Compile workflow with persistence
workflow = StateGraph(CarouselWorkflowState)
# ... add nodes and edges ...
app = workflow.compile(checkpointer=PostgresSaver(conn=db_pool))

# Human interrupt
async def review_phase(state):
    human_input = interrupt({"type": "review", "data": state.draft})
    if human_input["action"] == "approve":
        return {"approved": True}
    return {"approved": False, "feedback": human_input["feedback"]}
```

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| LangGraph API changes | Pin to minor version; review release notes monthly |
| Checkpoint storage growth | Adopt DeltaChannel (LangGraph 1.2+) |
| Non-deterministic replay | Use deterministic IDs; avoid `datetime.now()` in logic nodes |
| Human interrupt timeout | Set explicit timeouts; auto-reject after N hours |

## Related Decisions

- ADR-001: Adopt MADR for Architecture Decision Records
- ADR-004: Adopt Event-Driven Architecture for Content Workflows
- ADR-007: Use PostgreSQL for Primary Persistence

## Tags

#architecture #ai #workflow #langgraph
