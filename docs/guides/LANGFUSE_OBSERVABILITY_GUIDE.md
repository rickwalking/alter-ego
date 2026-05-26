# Langfuse Observability Guide for Alter-Ego

**Version:** 1.0
**Date:** 2026-05-23
**Status:** Active
**Applies to:** Backend AI agents, LangGraph workflows, subagents

---

## Table of Contents

1. [Current Implementation](#1-current-implementation)
2. [Observability Requirements for Pivot](#2-observability-requirements-for-pivot)
3. [Trace Structure](#3-trace-structure)
4. [Metadata Standards](#4-metadata-standards)
5. [Multi-Agent Workflow Tracing](#5-multi-agent-workflow-tracing)
6. [Cost Tracking](#6-cost-tracking)
7. [Dashboard Configuration](#7-dashboard-configuration)
8. [Alerting Rules](#8-alerting-rules)
9. [Implementation Examples](#9-implementation-examples)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Current Implementation

### 1.1 Langfuse Setup

```python
# src/rag_backend/monitoring_langfuse.py
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

_langfuse_handler: CallbackHandler | None = None

def init_langfuse(public_key: str, secret_key: str, host: str) -> CallbackHandler | None:
    """Initialize Langfuse tracing. Called once at application startup."""
    if not secret_key:
        return None

    os.environ.setdefault("LANGFUSE_SECRET_KEY", secret_key)
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", public_key)
    os.environ.setdefault("LANGFUSE_HOST", host)

    Langfuse(secret_key=secret_key, public_key=public_key, host=host)
    handler = CallbackHandler(public_key=public_key)
    _langfuse_handler = handler
    return handler

def get_langfuse_handler() -> CallbackHandler | None:
    """Get the global Langfuse callback handler."""
    return _langfuse_handler
```

### 1.2 Current Usage in Agents

```python
# In any agent that uses LangChain
from rag_backend.monitoring_langfuse import get_langfuse_handler

# Pass handler to LangChain callbacks
llm = ChatOpenAI(callbacks=[get_langfuse_handler()])
chain = prompt | llm
result = await chain.ainvoke(input, config={"callbacks": [get_langfuse_handler()]})
```

### 1.3 Configuration (Environment Variables)

```bash
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=http://langfuse:3000  # Internal Docker network
```

---

## 2. Observability Requirements for Pivot

The pivot introduces:
- **Multi-phase workflows** (7 phases for carousels, 4 states for blog posts)
- **Parallel subagents** (research, content drafting, image generation)
- **Human approval gates** (interrupt points)
- **Quality scoring** (rubric evaluation)
- **Persona enforcement** (voice matching)

Each of these needs tracing to answer:
- Where is the workflow stuck?
- Which phase costs the most?
- Why was this content rejected?
- How accurate is our quality scoring?
- Are subagents completing successfully?

---

## 3. Trace Structure

### 3.1 Top-Level Trace (One per Workflow)

```
Trace: carousel_workflow_abc123
├── Metadata: {project_id, user_id, content_type, persona_id}
├── Tags: ["carousel", "workflow", "v1.2"]
│
├── Span: phase_research (45s)
│   ├── Generation: research_agent_call (12s, 3.2k tokens)
│   └── Generation: research_agent_call (11s, 2.8k tokens)
│
├── Span: phase_outline (8s)
│   └── Generation: outline_agent (8s, 1.5k tokens)
│
├── Span: phase_content (120s)
│   ├── Generation: content_slide_1 (15s, 2.1k tokens)
│   ├── Generation: content_slide_2 (14s, 2.0k tokens)
│   ├── Generation: content_slide_3 (16s, 2.3k tokens)
│   └── ... (parallel subagents)
│
├── Span: phase_design (5s)
│   └── No LLM calls (deterministic)
│
├── Span: phase_images (180s)
│   ├── Generation: image_slide_1 (DALL-E, 18s)
│   ├── Generation: image_slide_2 (DALL-E, 19s)
│   └── ... (parallel image generation)
│
├── Span: quality_check (12s)
│   └── Generation: quality_agent (12s, 4.5k tokens)
│
└── Span: human_review (24h timeout)
    └── Event: human_approved (metadata: reviewer_id, feedback)
```

### 3.2 Key Principle

**One Trace = One Project/Post.** All spans and generations within a trace share the same `project_id` metadata, enabling full workflow visibility.

---

## 4. Metadata Standards

### 4.1 Required Fields (All Traces)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `project_id` | string | UUID of the carousel/blog project | `"550e8400-e29b-41d4-a716-446655440000"` |
| `user_id` | string | Creator/reviewer user ID | `"pedro-user-id"` |
| `content_type` | string | Type of content | `"carousel"`, `"blog_post"`, `"chat"` |
| `phase` | string | Current workflow phase | `"research"`, `"content_drafting"`, `"image_generation"` |
| `agent_name` | string | Agent or subagent name | `"researcher"`, `"content_drafter"`, `"quality_agent"` |
| `persona_id` | string | Persona profile used | `"pedro_professional_voice"` |
| `rubric_id` | string | Quality rubric applied | `"instagram_carousel_standard"` |

### 4.2 Optional Fields (Contextual)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `slide_index` | int | For per-slide operations | `3` |
| `version` | string | Prompt/agent version | `"v1"`, `"v2"` |
| `model` | string | LLM model used | `"claude-sonnet-4-20250514"` |
| `retry_count` | int | Number of retries | `2` |
| `source_count` | int | Number of sources used | `5` |
| `tool_name` | string | Tool invoked | `"web_search"`, `"refine_carousel_copy"` |

### 4.3 Tags

| Tag | When to Use |
|-----|-------------|
| `workflow` | Top-level workflow traces |
| `subagent` | Subagent execution spans |
| `human_in_the_loop` | Traces involving `interrupt()` |
| `quality_check` | Rubric evaluation spans |
| `persona_enforcement` | Voice matching spans |
| `error` | Traces with failures |
| `retry` | Traces that required retries |

---

## 5. Multi-Agent Workflow Tracing

### 5.1 Using `propagate_attributes` for Group Tracing

```python
from langfuse import propagate_attributes
from rag_backend.monitoring_langfuse import get_langfuse_handler

async def run_workflow_phase(project_id: str, phase: str, agent_name: str):
    """Run a workflow phase with proper Langfuse tracing."""

    # All child observations inherit this metadata
    with propagate_attributes(
        metadata={
            "project_id": project_id,
            "phase": phase,
            "agent_name": agent_name,
            "content_type": "carousel",
        }
    ):
        handler = get_langfuse_handler()

        # This call and all nested calls get the metadata
        result = await agent.ainvoke(
            input,
            config={"callbacks": [handler]},
        )

    return result
```

### 5.2 Tracing Subagents

```python
async def spawn_research_subagent(project_id: str, topic: str):
    """Spawn a research subagent with isolated but linked tracing."""

    # Create a child span within the parent trace
    langfuse = get_langfuse_client()  # Add this function to monitoring_langfuse.py

    with langfuse.start_as_current_observation(
        as_type="span",
        name="research_subagent",
        metadata={
            "project_id": project_id,
            "phase": "research",
            "agent_name": "researcher",
            "topic": topic,
        },
        tags=["subagent", "research"],
    ):
        handler = get_langfuse_handler()
        result = await research_agent.ainvoke(
            {"topic": topic},
            config={"callbacks": [handler]},
        )

    return result
```

### 5.3 Tracing Human Interrupts

```python
async def human_review_gate(state: WorkflowState):
    """Pause workflow for human review with tracing."""

    langfuse = get_langfuse_client()

    # Create a span that tracks how long human took
    with langfuse.start_as_current_observation(
        as_type="span",
        name="human_review",
        metadata={
            "project_id": state["project_id"],
            "phase": state["current_phase"],
            "content_preview": state["draft"][:200],
        },
        tags=["human_in_the_loop"],
    ) as span:

        # Emit event: review requested
        langfuse.event(
            name="review_requested",
            metadata={"timeout_hours": 24},
        )

        # Wait for human (interrupt)
        response = interrupt({
            "type": "review",
            "data": state["draft"],
        })

        # Emit event: review completed
        langfuse.event(
            name="review_completed",
            metadata={
                "action": response["action"],
                "reviewer_id": response["user_id"],
                "time_to_respond_seconds": response["response_time"],
            },
        )

        # Update span with outcome
        span.update(
            metadata={"action": response["action"]},
        )

    return response
```

---

## 6. Cost Tracking

### 6.1 Per-Phase Cost Breakdown

Track token usage per phase to understand where money is spent:

| Phase | Est. Tokens | Est. Cost | % of Total |
|-------|-------------|-----------|------------|
| Research | 45k | $0.03 | 1% |
| Outline | 10k | $0.15 | 4% |
| Content | 120k | $1.80 | 43% |
| Design | 5k | $0.08 | 2% |
| Images | N/A | $2.00 | 48% |
| Quality | 8k | $0.01 | <1% |
| **Total** | **~188k** | **~$4.07** | **100%** |

### 6.2 Cost Optimization Alerts

```yaml
# Alert: Content phase exceeding budget
rule: content_phase_cost > $3.00
action: notify_team("Carousel content phase exceeded $3 budget")
severity: warning

# Alert: Image generation failures
rule: image_phase_failure_rate > 20%
action: notify_team("Image generation failing frequently")
severity: critical

# Alert: Total workflow cost
rule: total_cost > $10.00
action: notify_team("Carousel cost exceeded $10")
severity: warning
```

---

## 7. Dashboard Configuration

### 7.1 Recommended Dashboards

#### Dashboard: Workflow Overview

| Widget | Query | Purpose |
|--------|-------|---------|
| Active Workflows | `traces where metadata.phase != "published"` | See what's in progress |
| Avg. Time to Publish | `avg(duration) by content_type` | Track velocity |
| Phase Bottleneck | `avg(duration) by metadata.phase` | Find slowest phase |
| Human Review Queue | `traces where tags include "human_in_the_loop"` | Pending approvals |

#### Dashboard: Quality Metrics

| Widget | Query | Purpose |
|--------|-------|---------|
| Avg Quality Score | `avg(metadata.quality_score)` | Overall quality trend |
| Rejection Rate | `count(action=reject) / count(total)` | How often content rejected |
| Voice Match Scores | `avg(metadata.voice_match_score)` | Persona consistency |
| Top Failure Reasons | `group by metadata.rejection_reason` | Why content fails |

#### Dashboard: Cost Analysis

| Widget | Query | Purpose |
|--------|-------|---------|
| Daily Spend | `sum(cost) by day` | Budget tracking |
| Cost by Phase | `sum(cost) by metadata.phase` | Where money goes |
| Token Usage | `sum(tokens) by model` | Model efficiency |
| Cost per Content | `avg(cost) by content_type` | Unit economics |

### 7.2 Custom Metrics to Track

```python
# After each workflow completion
langfuse.score(
    name="quality_score",
    value=quality_result["overall_score"],
    trace_id=trace_id,
)

langfuse.score(
    name="voice_match_score",
    value=persona_result["voice_match"],
    trace_id=trace_id,
)

langfuse.score(
    name="originality_score",
    value=quality_result["originality"],
    trace_id=trace_id,
)
```

---

## 8. Alerting Rules

### 8.1 Workflow Health

```yaml
# Stuck workflows
name: stuck_workflows
condition: traces where metadata.phase != "published" AND age > 48h
severity: warning
action: notify("Workflow stuck for >48h")

# High failure rate
name: high_failure_rate
condition: failure_rate > 10% in last 1h
severity: critical
action: pagerduty("AI workflow failure rate critical")

# Timeout alerts
name: human_review_timeout
condition: traces where tags include "human_in_the_loop" AND age > 24h
severity: info
action: auto_reject_workflow()
```

### 8.2 Cost Alerts

```yaml
# Budget threshold
name: daily_budget
condition: sum(cost) today > $100
severity: warning
action: notify("Daily AI budget exceeded")

# Anomaly detection
name: cost_anomaly
condition: cost > 2 * avg(cost, last_7_days)
severity: warning
action: notify("Unusual cost spike detected")
```

### 8.3 Quality Alerts

```yaml
# Quality degradation
name: quality_degradation
condition: avg(quality_score, last_24h) < avg(quality_score, last_7d) * 0.8
severity: warning
action: notify("Quality scores declining")

# Rejection spike
name: rejection_spike
condition: rejection_rate > 30% in last 4h
severity: warning
action: notify("High rejection rate — check persona/rubric")
```

---

## 9. Implementation Examples

### 9.1 Adding Langfuse Client Accessor

```python
# src/rag_backend/monitoring_langfuse.py
from langfuse import Langfuse

_langfuse_client: Langfuse | None = None


def get_langfuse_client() -> Langfuse | None:
    """Get the Langfuse client for manual span creation."""
    return _langfuse_client


def init_langfuse(...) -> CallbackHandler | None:
    global _langfuse_handler, _langfuse_client

    # ... existing code ...

    _langfuse_client = Langfuse(
        secret_key=secret_key,
        public_key=public_key,
        host=host,
    )

    # ... rest of existing code ...
```

### 9.2 Complete Workflow Tracing Example

```python
async def run_carousel_workflow(project_id: str, brief: dict):
    """Run full carousel workflow with comprehensive tracing."""

    langfuse = get_langfuse_client()
    handler = get_langfuse_handler()

    # Create root trace
    trace = langfuse.trace(
        name="carousel_workflow",
        metadata={
            "project_id": project_id,
            "user_id": brief["user_id"],
            "content_type": "carousel",
            "persona_id": brief.get("persona_id"),
            "rubric_id": brief.get("rubric_id"),
        },
        tags=["workflow", "carousel"],
    )

    try:
        # Phase 1: Research
        with trace.span(name="research", metadata={"phase": "research"}) as span:
            findings = await run_research(brief, handler)
            span.update(metadata={"sources_found": len(findings)})

        # Phase 2: Outline
        with trace.span(name="outline", metadata={"phase": "outline"}) as span:
            outline = await generate_outline(findings, brief, handler)
            span.update(metadata={"slide_count": len(outline)})

        # Phase 3: Content (parallel subagents)
        with trace.span(name="content", metadata={"phase": "content"}) as span:
            drafts = await draft_all_slides(outline, brief, handler)
            span.update(metadata={"slides_drafted": len(drafts)})

        # ... more phases ...

        # Final quality score
        trace.score(name="quality", value=quality_result["overall"])
        trace.score(name="voice_match", value=persona_result["match"])

        trace.update(status="success")

    except Exception as e:
        trace.update(status="error", metadata={"error": str(e)})
        raise
```

### 9.3 Frontend Error Tracking

While Langfuse is backend-focused, frontend errors related to AI workflows should be tracked:

```typescript
// Send frontend errors to backend for Langfuse correlation
async function logFrontendError(error: Error, context: WorkflowContext) {
  await fetch('/api/log/error', {
    method: 'POST',
    body: JSON.stringify({
      error: error.message,
      stack: error.stack,
      project_id: context.projectId,
      phase: context.phase,
      user_id: context.userId,
      trace_id: context.traceId,  // Correlate with backend trace
    }),
  });
}
```

---

## 10. Troubleshooting

### 10.1 Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Traces not appearing | `LANGFUSE_SECRET_KEY` not set | Check environment variables |
| Missing metadata | `propagate_attributes` not used | Wrap workflow phases with context manager |
| Orphaned spans | Subagent trace not linked | Use `start_as_current_observation` with parent context |
| High latency | Tracing overhead | Langfuse async is minimal; check network to Langfuse server |
| Cost not tracked | Image generation not instrumented | Add manual spans for non-LLM operations |

### 10.2 Debugging Traces

```python
# Enable debug logging for Langfuse
import logging
logging.getLogger("langfuse").setLevel(logging.DEBUG)

# Verify handler is initialized
handler = get_langfuse_handler()
print(f"Handler initialized: {handler is not None}")
print(f"Handler public key: {handler.public_key if handler else 'N/A'}")

# Manual trace test
from langfuse import Langfuse

lf = Langfuse()
trace = lf.trace(name="test", metadata={"test": True})
trace.generation(name="test_gen", model="gpt-4")
lf.flush()  # Ensure it's sent
```

---

## Related Documents

- [Langfuse Documentation](https://langfuse.com/docs)
- [LangChain Integration Guide](https://langfuse.com/docs/integrations/frameworks/langchain)
- [LangGraph Integration](https://langfuse.com/docs/integrations/frameworks/langgraph)
- [ADR-002: Use LangGraph for Workflow Engine](../docs/decisions/0002-use-langgraph-for-workflow-engine.md)
- [LangGraph Deep Agents Guide](../docs/architecture/langchain-deep-agents-guide.md)

---

**End of Langfuse Observability Guide**
