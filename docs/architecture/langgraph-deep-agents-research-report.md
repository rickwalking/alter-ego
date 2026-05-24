# LangChain Deep Agents, LangGraph Multi-Agent Patterns & Production Architectures

**Research Report — Alter-Ego Project**
*Compiled from: docs.langchain.com, blog.langchain.dev, LangGraph GitHub examples*

---

## Table of Contents

1. [Definitions and Concepts](#1-definitions-and-concepts)
2. [Recommended Multi-Agent Patterns](#2-recommended-multi-agent-patterns)
3. [Human-in-the-Loop Interrupts for Production](#3-human-in-the-loop-interrupts-for-production)
4. [Real-World Examples](#4-real-world-examples)
5. [Anti-Patterns and Common Failures](#5-anti-patterns-and-common-failures)
6. [State Persistence, Checkpoints, and Resumability](#6-state-persistence-checkpoints-and-resumability)
7. [Agent Memory Best Practices](#7-agent-memory-best-practices)
8. [Recommendations for Carousel/Blog Workflow](#8-recommendations-for-carouselblog-workflow)

---

## 1. Definitions and Concepts

### What Are "Deep Agents"?

Deep Agents are a **higher-level "agent harness"** built on top of LangChain and LangGraph. They provide "batteries-included" capabilities for complex, long-running tasks that go far beyond a simple tool-calling loop.

**Key capabilities that distinguish Deep Agents from simple agents:**

| Feature | Simple Agent (`create_agent`) | Deep Agent (`create_deep_agent`) |
|---|---|---|
| Core loop | Tool calling loop | Tool calling + planning + subagents |
| Context management | Manual (in prompt) | Virtual filesystem, auto-summarization |
| Planning | None built-in | Built-in `write_todos` tool |
| Subagent spawning | Manual | Built-in `task` tool for context isolation |
| Shell execution | None | `execute` tool via sandbox backends |
| Interpreter | None | QuickJS `eval` tool for programmatic tool composition |
| Memory | Thread-scoped only | Long-term memory via LangGraph Store |
| Human-in-the-loop | Manual interrupt setup | `interrupt_on` parameter per tool |
| Filesystem | None | Pluggable backends (in-memory, disk, LangGraph store, sandboxes) |
| Permissions | None | Declarative permission rules per file/dir |

**From the docs:**
> "`deepagents` is a standalone library built on top of LangChain's core building blocks for agents. It uses the LangGraph runtime for durable execution, streaming, human-in-the-loop, and other features."

**When to use each:**
- **Simple agents**: Quick prototypes, simple Q&A with tools, low-latency requirements
- **Deep Agents**: Complex multi-step tasks, coding agents, research workflows, anything requiring planning/context offloading
- **Raw LangGraph**: When you need full control over graph topology, state schema, and execution flow

### LangGraph as the Orchestration Runtime

LangGraph is the **low-level orchestration framework** beneath both simple and deep agents. It provides:

- **Durable execution**: Save progress and resume after failures/interrupts
- **Human-in-the-loop**: Pause execution at any point
- **Comprehensive memory**: Short-term (thread-scoped) and long-term (cross-thread) memory
- **Streaming**: Real-time token and state streaming
- **Persistence**: Checkpoint state at every super-step

LangGraph is inspired by Google's **Pregel** and **Apache Beam**. Execution proceeds in discrete **super-steps** where all scheduled nodes run (potentially in parallel).

---

## 2. Recommended Multi-Agent Patterns

LangChain docs define **5 core multi-agent patterns**, each suited to different use cases:

### Pattern Comparison Matrix

| Pattern | Distributed Dev | Parallelization | Multi-hop | Direct User Interaction | Best For |
|---|---|---|---|---|---|
| **Subagents** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | Complex tasks with isolated context domains |
| **Handoffs** | - | - | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Conversational flows where agents take turns |
| **Skills** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Simple tasks with on-demand specialized knowledge |
| **Router** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | - | ⭐⭐⭐ | Classifying and dispatching to parallel workers |
| **Custom Workflow** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Any complex deterministic + agentic mix |

### 2.1 Subagents Pattern

A **main agent coordinates subagents as tools**. All routing passes through the main agent, which decides when and how to invoke each subagent.

```python
from langchain.agents import create_agent
from langchain.tools import tool

# Subagent 1: Research specialist
research_agent = create_agent(
    model="gpt-5.4-mini",
    tools=[internet_search],
    prompt="You are a research specialist. Be thorough and cite sources.",
)

# Subagent 2: Writing specialist
writer_agent = create_agent(
    model="gpt-5.4-mini",
    tools=[format_document],
    prompt="You are a writing specialist. Produce polished output.",
)

# Wrap as tools for main agent
@tool
def ask_researcher(query: str) -> str:
    """Ask the research specialist."""
    response = research_agent.invoke({"messages": [{"role": "user", "content": query}]})
    return response["messages"][-1].content

@tool
def ask_writer(draft: str) -> str:
    """Ask the writing specialist to improve text."""
    response = writer_agent.invoke({"messages": [{"role": "user", "content": draft}]})
    return response["messages"][-1].content

# Main orchestrator
main_agent = create_agent(
    model="gpt-5.4",
    tools=[ask_researcher, ask_writer],
    prompt="You orchestrate research and writing tasks.",
    checkpointer=MemorySaver(),
)
```

**Tradeoffs:**
- ✅ Strong context isolation — each subagent only sees its relevant context
- ✅ Parallel execution possible
- ✅ Centralized control and auditability
- ❌ Extra model call overhead (results flow back through main agent)
- ❌ Stateless by design — each invocation starts fresh

### 2.2 Handoffs Pattern

Agents **transfer control to each other** via tool calls. Each agent can hand off to others or respond directly to the user.

```python
from langchain.agents import create_agent
from langgraph.types import Command

# Agent A can hand off to Agent B by returning a tool call
# that updates a "current_agent" state variable

# In LangGraph Graph API:
def route_to_agent(state):
    if state["intent"] == "billing":
        return Command(goto="billing_agent")
    elif state["intent"] == "technical":
        return Command(goto="tech_agent")
    return Command(goto="END")
```

**Tradeoffs:**
- ✅ Natural for conversational flows
- ✅ Stateful — the active agent persists across turns
- ✅ Direct user interaction possible
- ❌ Sequential execution only
- ❌ Less suitable for parallel multi-domain tasks

### 2.3 Skills Pattern

A **single agent loads specialized prompts and knowledge on-demand**. The agent stays in control while loading context from skills as needed.

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="openai:gpt-5.4",
    skills=["sales_playbook", "technical_reference"],
    # Skills are loaded into filesystem/middleware on demand
)
```

**Tradeoffs:**
- ✅ Simplest to implement and maintain
- ✅ Best for repeat requests (skill context stays loaded)
- ❌ All context accumulates in main agent's history
- ❌ Less isolation than subagents

### 2.4 Router Pattern

A **routing step classifies input** and directs it to one or more specialized agents. Results are synthesized into a combined response.

```python
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    query: str
    category: str
    result: str

def router(state: State):
    # LLM classifies the query
    category = classify_query(state["query"])
    return {"category": category}

def dispatch(state: State):
    if state["category"] == "code":
        return Command(goto="code_agent")
    elif state["category"] == "design":
        return Command(goto="design_agent")
    return Command(goto="general_agent")

builder = StateGraph(State)
builder.add_node("router", router)
builder.add_node("code_agent", code_subgraph)
builder.add_node("design_agent", design_subgraph)
builder.add_conditional_edges("router", dispatch)
builder.add_edge(START, "router")
```

**Tradeoffs:**
- ✅ Explicit routing logic
- ✅ Parallel execution of multiple agents possible
- ✅ Similar efficiency to subagents for multi-domain tasks
- ❌ Router itself is an extra LLM call

### 2.5 Custom Workflow (LangGraph StateGraph)

Build **bespoke execution flows** mixing deterministic logic and agentic behavior. Embed any other pattern as nodes.

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver

class BlogWorkflowState(MessagesState):
    research_notes: str
    draft: str
    review_feedback: str
    final_output: str

def research_node(state: BlogWorkflowState):
    # Could be a subagent or direct LLM call
    notes = research_agent.invoke(state["messages"][-1].content)
    return {"research_notes": notes}

def draft_node(state: BlogWorkflowState):
    draft = writer_agent.invoke(state["research_notes"])
    return {"draft": draft}

def review_node(state: BlogWorkflowState):
    # Human-in-the-loop interrupt
    feedback = interrupt({"draft": state["draft"], "action": "Please review"})
    return {"review_feedback": feedback}

def finalize_node(state: BlogWorkflowState):
    final = editor_agent.invoke(state["review_feedback"])
    return {"final_output": final}

builder = StateGraph(BlogWorkflowState)
builder.add_node("research", research_node)
builder.add_node("draft", draft_node)
builder.add_node("review", review_node)
builder.add_node("finalize", finalize_node)
builder.add_edge(START, "research")
builder.add_edge("research", "draft")
builder.add_edge("draft", "review")
builder.add_edge("review", "finalize")
builder.add_edge("finalize", END)

graph = builder.compile(checkpointer=MemorySaver())
```

### Performance Comparison (from official docs)

| Scenario | Subagents | Handoffs | Skills | Router |
|---|---|---|---|---|
| One-shot "buy coffee" | 4 calls | 3 calls | 3 calls | 3 calls |
| Repeat "buy coffee again" | 8 calls total | 5 calls total | 5 calls total | 6 calls total |
| Multi-domain comparison | 5 calls, ~9K tokens | 7+ calls, ~14K tokens | 3 calls, ~15K tokens | 5 calls, ~9K tokens |

**Key insight:** Subagents and Router excel at parallel multi-domain work. Handoffs and Skills are most efficient for repeat/conversational tasks.

---

## 3. Human-in-the-Loop Interrupts for Production

### Core Mechanism

LangGraph's `interrupt()` function pauses graph execution at any point and waits for external input:

```python
from langgraph.types import interrupt, Command

def approval_node(state: State):
    # Pause and ask for approval
    approved = interrupt({
        "question": "Do you approve this action?",
        "details": state["action_details"]
    })
    return {"approved": approved}

# Resume with:
graph.invoke(Command(resume=True), config=config, version="v2")
```

**What happens under the hood:**
1. Graph execution suspends at the exact `interrupt()` call
2. State is saved via the checkpointer
3. The interrupt payload is returned to the caller
4. Graph waits indefinitely
5. On resume, the value becomes the return value of `interrupt()`

### Production Patterns

#### Approval Workflows
```python
def approval_node(state: State) -> Command[Literal["proceed", "cancel"]]:
    decision = interrupt({
        "question": "Approve this action?",
        "details": state["action_details"],
    })
    return Command(goto="proceed" if decision else "cancel")
```

#### Review and Edit State
```python
def review_node(state: State):
    edited = interrupt({
        "instruction": "Review and edit this content",
        "content": state["generated_text"]
    })
    return {"generated_text": edited}
```

#### Interrupts Inside Tools
```python
@tool
def send_email(to: str, subject: str, body: str):
    response = interrupt({
        "action": "send_email",
        "to": to, "subject": subject, "body": body,
        "message": "Approve sending this email?"
    })
    if response.get("action") == "approve":
        # Execute with potentially edited args
        final_to = response.get("to", to)
        ...
```

#### Deep Agents HITL Configuration
```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="openai:gpt-5.4",
    tools=[remove_file, fetch_file, notify_email],
    interrupt_on={
        "remove_file": True,  # Default: approve, edit, reject, respond
        "fetch_file": False,  # No interrupt
        "notify_email": {"allowed_decisions": ["approve", "reject"]},
    },
    checkpointer=checkpointer,  # REQUIRED
)
```

### Critical Production Rules

1. **Always use a durable checkpointer** — `MemorySaver` for dev, `PostgresSaver` for production
2. **Always use the same `thread_id`** when resuming
3. **Do NOT wrap `interrupt()` in bare `try/except`** — it uses an internal exception to pause
4. **Do NOT conditionally skip or loop `interrupt()` calls** — matching is strictly index-based
5. **Do NOT pass complex/non-serializable objects** to `interrupt()` — use JSON-serializable values
6. **Side effects before `interrupt()` must be idempotent** — the node restarts from the beginning on resume

### Streaming with HITL

```python
for chunk in graph.stream(
    initial_input,
    stream_mode=["messages", "updates", "values"],
    subgraphs=True,
    config=config,
    version="v2",
):
    if chunk["type"] == "messages":
        # Stream AI response tokens
        display_streaming_content(chunk["data"])
    elif chunk["type"] == "values" and chunk.get("interrupts"):
        # Handle interrupt
        user_response = get_user_input(chunk["interrupts"][0].value)
        initial_input = Command(resume=user_response)
        break
```

---

## 4. Real-World Examples

### 4.1 LangChain GTM Agent (Deep Agents in Production)

**Use case:** Automated lead research and personalized email drafting for the LangChain sales team.

**Architecture:**
- Built on **Deep Agents** for multi-step orchestration
- Connected to Salesforce, Gong, LinkedIn, Exa (web search)
- Uses **subagents** for account intelligence (parallel per-account research)
- **Human-in-the-loop** via Slack — every draft requires rep approval
- **Memory loop:** Rep edits are analyzed and stored as stylistic preferences per rep

**Results:**
- Lead-to-opportunity conversion up **250%**
- Reps reclaimed **40 hours/month each**
- **50% daily active usage** across sales team
- 48-hour auto-send SLA for unreviewed drafts

**Key pattern:** Ambient agent triggered by Salesforce lead creation → research subagents run in parallel → main agent synthesizes → Slack HITL approval → auto-follow-ups.

### 4.2 Chat LangChain Rebuild (Subgraphs for Complex Q&A)

**Use case:** Public documentation chatbot that answers product questions with citations.

**Architecture:**
- **Simple mode:** `create_agent` with docs + knowledge base search tools (3-6 tool calls, sub-15s)
- **Deep mode:** Deep Agent with **3 specialized subgraphs**: docs search, knowledge base search, codebase search
- Each subagent asks follow-up questions, filters results, returns "golden data"
- Main orchestrator synthesizes into comprehensive answer

**Key insight:** They abandoned vector embeddings for docs. Instead, agents search full pages via API, scan article titles, then read full articles — mirroring human workflows.

**Middleware stack:**
```python
middleware = [
    guardrails_middleware,      # Filter off-topic queries
    model_retry_middleware,     # Retry on API failures
    model_fallback_middleware,  # Switch models if needed
    anthropic_cache_middleware, # Cache expensive calls
]
```

### 4.3 Reflection Agents (Self-Improvement Patterns)

Three documented reflection architectures:

1. **Basic Reflection:** Generator + Reflector loop. Fixed iterations. Simple but ungrounded.
2. **Reflexion:** Actor generates response + search queries → Revisor critiques with external citations → Loop.
3. **LATS (Language Agent Tree Search):** Monte Carlo tree search with reflection. Expand → Simulate → Reflect → Backpropagate.

All implemented as LangGraph `StateGraph` with conditional edges.

### 4.4 LangChain's Internal Support Agent

**Use case:** Complex debugging questions requiring docs, knowledge base, AND codebase analysis.

**Pattern:** Deep Agent with subagents running in parallel:
- Docs subagent searches Mintlify API for full pages
- KB subagent scans article titles then reads relevant ones
- Codebase subagent uses `ripgrep` → directory traversal → file reading with line numbers
- Main agent synthesizes all three into cited answer

**Why it works:** Each subagent filters raw search results down to "golden data" before passing to main agent, preventing context overload.

---

## 5. Anti-Patterns and Common Failures

### 5.1 Multi-Agent Anti-Patterns

| Anti-Pattern | Why It Fails | Solution |
|---|---|---|
| **Over-engineering with multi-agent** | Single agent with right tools often suffices | Start simple; add multi-agent only when context isolation or parallelization is needed |
| **Skills for multi-domain parallel tasks** | All skill context accumulates in agent history, causing token bloat | Use subagents or router for parallel multi-domain work |
| **Handoffs for parallel work** | Handoffs are sequential by design | Use subagents with parallel tool calling |
| **Subagents for simple repeated tasks** | Stateless subagents repeat full flow every time | Use skills or handoffs for repeated similar tasks |
| **Too many tools on one agent** | Agent makes poor tool selection decisions | Split into subagents with focused tool sets |
| **Nested subagents without checkpoint namespaces** | Parallel calls to same per-thread subagent cause checkpoint conflicts | Use per-invocation default, or wrap in unique `StateGraph` nodes |

### 5.2 LangGraph Execution Anti-Patterns

| Anti-Pattern | Why It Fails | Solution |
|---|---|---|
| **Wrapping `interrupt()` in bare `try/except`** | Catches the internal exception, breaking pause/resume | Separate interrupt calls from error-prone code; catch specific exceptions only |
| **Conditional/skipping `interrupt()` calls** | Index-based matching fails on resume | Keep interrupt calls in deterministic, consistent order |
| **Non-idempotent side effects before `interrupt()`** | Side effects re-run on every resume | Make operations idempotent (upserts), or place them AFTER interrupt |
| **Non-deterministic control flow outside tasks** | Random numbers, time checks change on resume | Wrap all non-determinism in `@task` decorators |
| **Side effects not in tasks (Functional API)** | File writes, API calls re-execute on resume | Wrap side effects in `@task` functions |
| **Returning non-serializable values from tasks** | Checkpointer fails to save state | Ensure all task outputs are JSON-serializable |
| **Mixing static edges and `Command(goto=...)` from same node** | Both paths execute, causing unexpected behavior | Use EITHER static edges OR dynamic routing per node |

### 5.3 Context Management Anti-Patterns

| Anti-Pattern | Why It Fails | Solution |
|---|---|---|
| **Chunking structured docs into embeddings** | Loses headers, structure, context | Give agents direct API access to full structured pages |
| **Dumping all tool results into model context** | Token explosion, degraded reasoning | Use interpreters to process/filter data before returning to model |
| **No summarization for long conversations** | Context window overflow | Use `SummarizationMiddleware` or manual message trimming |
| **Storing everything in short-term memory** | Thread-scoped state doesn't persist across sessions | Use LangGraph Store for long-term memory |

---

## 6. State Persistence, Checkpoints, and Resumability

### Core Concepts

**Threads:** A unique ID (`thread_id`) that identifies a checkpointed conversation/session.

**Checkpoints:** Snapshots of graph state saved at each **super-step** boundary.

**Super-steps:** A single "tick" of the graph where all scheduled nodes execute (potentially in parallel).

### Checkpointer Implementations

| Implementation | Library | Use Case |
|---|---|---|
| `InMemorySaver` | Built-in (`langgraph-checkpoint`) | Development, testing |
| `SqliteSaver` | `langgraph-checkpoint-sqlite` | Local workflows, experimentation |
| `PostgresSaver` | `langgraph-checkpoint-postgres` | **Production** (used in LangSmith) |
| `AsyncPostgresSaver` | `langgraph-checkpoint-postgres` | Production with async execution |
| `CosmosDBSaver` | `langchain-azure-cosmosdb` | Azure production deployments |

### Durability Modes

```python
graph.stream({"input": "test"}, durability="sync")
```

| Mode | Behavior | Tradeoff |
|---|---|---|
| `"exit"` | Persist only when graph exits (success/error/interrupt) | Best performance; cannot recover from mid-execution crashes |
| `"async"` | Persist asynchronously while next step executes | Good balance; small risk of lost checkpoint if process crashes during execution |
| `"sync"` | Persist synchronously before next step starts | **Highest durability**; some performance overhead |

### Delta Channels (LangGraph 1.2+)

**Problem:** Full-snapshot checkpointing grows at **O(N²)** for append-only state like messages and files. A coding agent running 200 turns serializes **5.3 GB** with full snapshots.

**Solution:** `DeltaChannel` stores only the diff at each step, with periodic full snapshots every K steps (default 50 for Deep Agents).

**Result:** Same 200-turn workload drops to **129 MB** — a **41× reduction**.

```python
from langgraph.channels.delta import DeltaChannel

def append(state: list[str], writes: list[list[str]]) -> list[str]:
    return state + [item for batch in writes for item in batch]

class MyAgentState(TypedDict):
    items: Annotated[list[str], DeltaChannel(reducer=append, snapshot_frequency=50)]
```

**Migration:** Existing threads work without migration. First checkpoint after upgrade begins writing deltas.

### Time Travel and Forking

```python
# Get full history
history = list(graph.get_state_history(config))

# Replay from a specific checkpoint
config_with_checkpoint = {
    "configurable": {
        "thread_id": "1",
        "checkpoint_id": "1ef663ba-28fe-6528-8002-5a559208592c"
    }
}
graph.invoke(None, config=config_with_checkpoint)  # Re-executes from checkpoint

# Update state (creates new checkpoint, doesn't modify original)
graph.update_state(config, {"foo": "new_value"}, as_node="some_node")
```

### Graceful Shutdown (LangGraph 1.2+)

```python
from langgraph.runtime import RunControl
from langgraph.errors import GraphDrained

control = RunControl()
signal.signal(signal.SIGTERM, lambda *_: control.request_drain("sigterm"))

try:
    result = graph.invoke(inputs, config, control=control)
except GraphDrained as e:
    # Checkpoint saved, resumable with same config
    log.info("graph drained: %s", e.reason)
    # Resume later: graph.invoke(None, config)
```

### Encryption

```python
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from langgraph.checkpoint.postgres import PostgresSaver

serde = EncryptedSerializer.from_pycryptodome_aes()  # reads LANGGRAPH_AES_KEY
checkpointer = PostgresSaver.from_conn_string("postgresql://...", serde=serde)
```

---

## 7. Agent Memory Best Practices

### Memory Types (from CoALA paper mapping)

| Memory Type | What is Stored | Human Example | Agent Example |
|---|---|---|---|
| **Semantic** | Facts | Things learned in school | Facts about a user (preferences, profile) |
| **Episodic** | Experiences | Things I did | Past agent actions, few-shot examples |
| **Procedural** | Instructions | Instincts, motor skills | System prompts, rules, agent code |

### Short-Term Memory (Thread-Scoped)

Managed by the **checkpointer**. Stores:
- Conversation history (`messages`)
- Uploaded files, retrieved documents
- Generated artifacts
- Any state keys defined in the graph schema

**Best practices:**
- Use `add_messages` reducer (not `operator.add`) to handle message ID tracking and overwriting
- Trim/summarize long conversations to prevent context window overflow
- Use `MessagesState` as base and extend with additional fields

```python
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages

class State(MessagesState):
    documents: list[str]
    research_notes: str
```

### Long-Term Memory (Cross-Thread)

Managed by the **LangGraph Store** (`BaseStore`). Memories are namespaced by tuples and searchable.

```python
from langgraph.store.memory import InMemoryStore
from langchain.embeddings import init_embeddings

store = InMemoryStore(
    index={
        "embed": init_embeddings("openai:text-embedding-3-small"),
        "dims": 1536,
        "fields": ["food_preference", "$"]
    }
)

# Save memory
store.put(("user_123", "memories"), "memory_1", {
    "food_preference": "I like pizza",
    "context": "Discussing dinner plans"
})

# Search memories
memories = store.search(
    ("user_123", "memories"),
    query="What does the user like to eat?",
    limit=3
)
```

**Two approaches for semantic memory:**

1. **Profile:** Single continuously-updated JSON document. Easier to retrieve full context, but harder to update without losing information.
2. **Collection:** Multiple narrowly-scoped documents. Easier to generate new memories, but harder to update/delete existing ones. Higher recall.

### Memory Writing Strategies

| Strategy | When | Pros | Cons |
|---|---|---|---|
| **Hot path** | Agent decides to save memories before responding | Real-time availability, transparent to user | Adds latency, agent must multitask |
| **Background** | Separate async process/cron generates memories | No latency impact, focused memory generation | May leave other threads without new context |

**Hot path example** (ChatGPT-style):
```python
# Agent has a save_memories tool
# Decides whether/how to upsert memories with each message
```

**Background example** (weekly cron):
```python
# Weekly cron compacts and deduplicates memories
# Runs independently of user-facing agent
```

### Accessing Memory in LangGraph Nodes

```python
from langgraph.runtime import Runtime
from dataclasses import dataclass

@dataclass
class Context:
    user_id: str

async def call_model(state: MessagesState, runtime: Runtime[Context]):
    user_id = runtime.context.user_id
    namespace = (user_id, "memories")

    # Retrieve relevant memories
    memories = await runtime.store.asearch(
        namespace,
        query=state["messages"][-1].content,
        limit=3
    )
    info = "\n".join([m.value.get("memory", "") for m in memories])

    # Use in model call
    ...
```

### Procedural Memory (Self-Improving Agents)

Agents can modify their own instructions via reflection:

```python
def update_instructions(state: State, store: BaseStore):
    namespace = ("instructions",)
    current = store.search(namespace)[0]

    prompt = f"""Current instructions: {current.value['instructions']}
    Recent feedback: {state['messages']}
    Refine the instructions based on feedback."""

    output = llm.invoke(prompt)
    new_instructions = output['new_instructions']
    store.put(("instructions",), "agent_a", {"instructions": new_instructions})
```

---

## 8. Recommendations for Carousel/Blog Workflow

Based on the Alter-Ego project's RAG-based carousel and blog generation workflow, here are specific architectural recommendations:

### Recommended Architecture: Custom Workflow + Subagents

For a carousel/blog generation system, the optimal pattern is a **Custom LangGraph Workflow** that uses **Subagents** for domain-specific tasks:

```
User Request
    |
    v
[Router Node] — Classifies request type (carousel vs blog vs both)
    |
    +---> [Research Subagent] — Parallel for each topic/source
    |         (Searches vector DB, web, internal knowledge)
    |
    +---> [Content Planning Node] — Determines slide/outline structure
    |
    +---> [Draft Generation Subagent] — Writes content per section
    |         (Parallel for carousel slides, sequential for blog sections)
    |
    +---> [Review Node] — HITL interrupt for human approval
    |
    +---> [Formatting Node] — Applies brand templates/styles
    |
    v
[Final Output]
```

### Why This Pattern Fits

1. **Research benefits from parallelism**: Multiple search queries (web, Pinecone, internal docs) can run simultaneously via subagents
2. **Context isolation matters**: The research subagent shouldn't see the brand voice guidelines; the writer subagent shouldn't be overwhelmed by raw search results
3. **HITL is non-negotiable**: Content generation needs human review before publishing — use `interrupt()` at the review node
4. **Reusability**: The research subagent can be reused across carousel, blog, and other content types

### Specific Implementation Guidance

**State Schema:**
```python
class ContentWorkflowState(MessagesState):
    request_type: Literal["carousel", "blog", "both"]
    topics: list[str]
    research_notes: Annotated[list[str], add]  # Append-only
    outline: str
    drafts: Annotated[list[str], add]
    review_feedback: str
    final_content: str
    metadata: dict  # Source citations, timestamps
```

**Subagent Design:**
- **Research Subagent:** Has access to search tools (Pinecone hybrid search, Tavily web search). Returns structured notes with citations. Compiled with `checkpointer=None` (per-invocation, fresh each time).
- **Writer Subagent:** Has access to brand guidelines skill, formatting tools. Receives only the relevant research notes for its section.
- **Fact-Checker Subagent:** (Optional) Validates claims against sources before finalization.

**Human-in-the-Loop Points:**
```python
def review_node(state: ContentWorkflowState):
    feedback = interrupt({
        "action": "review_content",
        "draft": state["drafts"],
        "request_type": state["request_type"],
        "message": "Please review the generated content. Approve, edit, or reject."
    })
    return {"review_feedback": feedback}
```

**Memory Strategy:**
- **Short-term (thread):** Conversation history, current request state via `PostgresSaver`
- **Long-term (store):**
  - User preferences: `(user_id, "preferences")` — content style, tone, format preferences
  - Past topics: `(user_id, "topics")` — what they've already covered to avoid duplication
  - Brand guidelines: `("brand", "guidelines")` — procedural memory
  - Performance data: `("analytics", "content_performance")` — which content types performed best

**Checkpointing:**
```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string("postgresql://...")
checkpointer.setup()  # Create tables

# Use sync durability for content generation (reliability > speed)
graph.invoke(inputs, config, durability="sync")
```

**Delta Channels:**
Enable for `messages` and any append-only lists (like `research_notes`, `drafts`) to prevent O(N²) storage growth as workflows get longer.

### Anti-Patterns to Avoid for This Use Case

| Don't Do | Why | Instead |
|---|---|---|
| Put all research + writing in one agent | Context window overflow, poor tool selection | Use subagents with isolated contexts |
| Use handoffs for parallel research | Handoffs are sequential | Use subagents with parallel tool calls |
| Skip HITL for "trusted" requests | Once published, bad content is public | Always review before finalize node; auto-approve only for drafts |
| Store all previous conversations in thread state | Checkpoint bloat | Use LangGraph Store for cross-thread memory; trim thread messages |
| Generate entire carousel in one LLM call | Exceeds context, loses structure | Generate outline first, then parallel slide generation |

### Technology Stack Alignment

Given the Alter-Ego stack (FastAPI + LangGraph + Pinecone + PostgreSQL):

- **LangGraph StateGraph** for the main workflow
- **`create_deep_agent` for subagents** (research, writing, fact-checking) to get virtual filesystem, planning, and summarization "for free"
- **PostgreSQL checkpointer** (`PostgresSaver`) for durable execution
- **LangGraph Store** backed by PostgreSQL for long-term memory
- **Pinecone** for vector search (used by research subagent as a tool)
- **LangSmith** for tracing every generation, evaluation, and regression detection

### Testing Strategy

1. **Build eval dataset** of representative requests before writing production code
2. **Mock external APIs** (Pinecone, web search) for controlled eval harness
3. **Rule-based evaluators:** Check outline structure, citation presence, brand guideline compliance
4. **LLM-as-judge evaluators:** Score tone, accuracy, formatting
5. **HITL metrics:** Track approve/edit/reject rates per subagent to identify weak points
6. **Run evals in CI** before deploying prompt/model changes

---

## Key References

- [Deep Agents Overview](https://docs.langchain.com/oss/python/deepagents/overview/)
- [LangGraph Overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [Multi-Agent Patterns](https://docs.langchain.com/oss/python/langchain/multi-agent)
- [Interrupts Guide](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [Persistence & Checkpoints](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Durable Execution](https://docs.langchain.com/oss/python/langgraph/durable-execution)
- [Memory Concepts](https://docs.langchain.com/oss/python/concepts/memory)
- [Subgraphs Guide](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
- [Delta Channels Blog Post](https://blog.langchain.dev/delta-channels-evolving-agent-runtime/)
- [GTM Agent Case Study](https://blog.langchain.dev/how-we-built-langchains-gtm-agent/)
- [Chat LangChain Rebuild](https://blog.langchain.dev/rebuilding-chat-langchain/)
- [Reflection Agents](https://blog.langchain.dev/reflection-agents/)
- [Agent Development Lifecycle](https://blog.langchain.dev/the-agent-development-lifecycle/)
- [Interpreters in Deep Agents](https://blog.langchain.dev/give-your-agents-an-interpreter/)
