# SSE Event-Name Inventory (Frozen)

Status: Frozen | Ticket: AE-0076 | Last verified: 2026-06-12

This document is the human-readable inventory of every Server-Sent Events
(SSE) event name and every Redis stream event type used by the Alter-Ego
system. It pairs with the machine-readable source-of-truth artifact
[`sse-event-inventory.json`](./sse-event-inventory.json), which the backend
and frontend contract tests read directly.

## Frozen-strings rule

These event-name strings are **string-frozen for the entire migration**
(frozen until **Phase 8**). No event renames, no payload changes, and no new
events are permitted while the freeze is in effect.

Because no external consumers exist, this freeze protects exactly one client —
the in-repo frontend. Under the migrate-in-place rule, a frozen name may be
changed **only** by updating, in a single PR:

1. this document,
2. the source-of-truth artifact `sse-event-inventory.json`,
3. the relevant backend constant module(s), and
4. the relevant frontend constant map(s).

The backend and frontend contract tests fail in CI on any drift between a
constant value and the artifact, so a conscious update of all four locations is
required for the test suite to pass again.

## Verified sources

The inventory was reconciled (2026-06-12) from these four verified sources:

| # | Source | Layer | Owns |
|---|--------|-------|------|
| 1 | `backend/src/rag_backend/application/services/carousel/editorial_workflow_sse_constants.py` | **application** | Carousel editorial workflow SSE event names |
| 2 | `backend/src/rag_backend/domain/constants/chat_stream.py` | **domain** | Chat streaming SSE event names |
| 3 | `backend/src/rag_backend/domain/constants/workflow_events.py` | **domain** | Redis stream name + workflow event types |
| 4 | `frontend/src/constants/editorial-workflow.ts` (`EDITORIAL_WORKFLOW_SSE_EVENTS`) and `frontend/src/lib/sse-client.ts` (`SSE_EVENT_TYPE`) | frontend | Frontend SSE event-name maps consumed by the SSE hooks |

> Note: the carousel editorial SSE names live in the **application layer**, not
> the domain layer. This is recorded deliberately for later
> module-ownership decisions in the modularization work.

## 1. Carousel editorial workflow SSE events

Module: `application/services/carousel/editorial_workflow_sse_constants.py`
(layer: **application**). Emitted via the editorial workflow SSE hub and
consumed by the frontend hook `use-editorial-workflow-sse.ts`.

| Constant | Value | Layer |
|----------|-------|-------|
| `SSE_EVENT_PHASE_CHANGE` | `phase_change` | application |
| `SSE_EVENT_PROGRESS` | `progress` | application |
| `SSE_EVENT_REVIEW_REQUIRED` | `review_required` | application |
| `SSE_EVENT_ERROR` | `error` | application |
| `SSE_EVENT_ARTIFACT` | `artifact` | application |
| `SSE_EVENT_KEEPALIVE` | `_keepalive` | application |

## 2. Chat streaming SSE events

Module: `domain/constants/chat_stream.py` (layer: **domain**). Emitted by
`application/services/chat_stream_service.py` (which imports these constants)
and consumed by the frontend `SSE_EVENT_TYPE` map.

| Constant | Value | Layer |
|----------|-------|-------|
| `SSE_EVENT_TOKEN` | `token` | domain |
| `SSE_EVENT_SOURCES` | `sources` | domain |
| `SSE_EVENT_COMPLETE` | `complete` | domain |
| `SSE_EVENT_ERROR` | `error` | domain |
| `SSE_EVENT_TOOL_RESULT` | `tool_result` | domain |

## 3. Redis stream name and workflow event types

Module: `domain/constants/workflow_events.py` (layer: **domain**). These are
the event-driven architecture (ADR-004) Redis Streams event types, not SSE
wire names. Frozen alongside the SSE names because the streaming-slice work
diffs this inventory.

| Constant | Value | Layer |
|----------|-------|-------|
| `STREAM_CONTENT_EVENTS` | `content.events` | domain |
| `EVENT_TYPE_PROJECT_PHASE_CHANGED` | `content.project.phase_changed` | domain |
| `EVENT_TYPE_PROJECT_REVIEW_REQUESTED` | `content.project.review.requested` | domain |
| `EVENT_TYPE_PROJECT_REVIEW_COMPLETED` | `content.project.review.completed` | domain |
| `EVENT_TYPE_BLOGPOST_STATUS_CHANGED` | `content.blogpost.status.changed` | domain |
| `EVENT_TYPE_BLOGPOST_SCHEDULED` | `content.blogpost.scheduled` | domain |
| `EVENT_TYPE_BLOGPOST_PUBLISHED` | `content.blogpost.published` | domain |
| `EVENT_TYPE_BLOGPOST_CREATED` | `content.blogpost.created` | domain |
| `EVENT_TYPE_BLOGPOST_UPDATED` | `content.blogpost.updated` | domain |
| `EVENT_TYPE_BLOGPOST_DELETED` | `content.blogpost.deleted` | domain |
| `EVENT_TYPE_BLOGPOST_COMMENT_ADDED` | `content.blogpost.comment.added` | domain |
| `EVENT_TYPE_BLOGPOST_VERSION_RESTORED` | `content.blogpost.version.restored` | domain |
| `EVENT_TYPE_BLOGPOST_AI_ACTION` | `content.blogpost.ai.action` | domain |
| `EVENT_TYPE_NOTIFICATION_CREATED` | `content.notification.created` | domain |

## 4. Frontend SSE event-name maps

Layer: frontend. The frontend subscribes via these named constants, never via
raw string literals in the SSE hooks. Both maps must equal the backend values
above; the frontend contract test enforces this against the artifact.

### `EDITORIAL_WORKFLOW_SSE_EVENTS` (`src/constants/editorial-workflow.ts`)

Consumed by `src/features/create/hooks/use-editorial-workflow-sse.ts`.

| Key | Value | Mirrors backend |
|-----|-------|-----------------|
| `PHASE_CHANGED` | `phase_change` | `SSE_EVENT_PHASE_CHANGE` |
| `PROGRESS` | `progress` | `SSE_EVENT_PROGRESS` |
| `REVIEW_REQUIRED` | `review_required` | `SSE_EVENT_REVIEW_REQUIRED` |
| `ERROR` | `error` | `SSE_EVENT_ERROR` |
| `ARTIFACT` | `artifact` | `SSE_EVENT_ARTIFACT` |

> `SSE_EVENT_KEEPALIVE` (`_keepalive`) has no frontend key: the keepalive is a
> server-side proxy heartbeat and is never subscribed to by the client.

### `SSE_EVENT_TYPE` (`src/lib/sse-client.ts`)

Consumed by `src/features/chat/hooks/use-sse-chat.ts`.

| Key | Value | Mirrors backend |
|-----|-------|-----------------|
| `TOKEN` | `token` | `SSE_EVENT_TOKEN` |
| `COMPLETE` | `complete` | `SSE_EVENT_COMPLETE` |
| `ERROR` | `error` | `SSE_EVENT_ERROR` |
| `SOURCES` | `sources` | `SSE_EVENT_SOURCES` |
| `TOOL_RESULT` | `tool_result` | `SSE_EVENT_TOOL_RESULT` |

## Inline event-name literals outside the constant modules

The `rg` sweep (2026-06-12) found **zero** inline event-name literals in the
carousel editorial workflow routes/services and the chat stream service — these
all use the constant modules above.

The sweep did find inline literals of the **chat** event vocabulary
(`token`, `sources`, `complete`, `tool_result`) in the agent layer and one
non-streaming route. They are recorded here per AE-0076 AC (rather than
refactored) to keep SSE behavior byte-identical during the freeze:

| Location | Inline literals | Equivalent constant (`chat_stream.py`) |
|----------|-----------------|----------------------------------------|
| `backend/src/rag_backend/agents/alter_ego_agent.py` (L184, L205, L215, L253) | `tool_result`, `token`, `complete` | `SSE_EVENT_TOOL_RESULT`, `SSE_EVENT_TOKEN`, `SSE_EVENT_COMPLETE` |
| `backend/src/rag_backend/agents/rag_agent.py` (L237, L258, L269, L270, L307) | `tool_result`, `token`, `sources`, `complete` | `SSE_EVENT_TOOL_RESULT`, `SSE_EVENT_TOKEN`, `SSE_EVENT_SOURCES`, `SSE_EVENT_COMPLETE` |
| `backend/src/rag_backend/api/routes/conversations.py` (L398, L400) | `complete`, `sources` | `SSE_EVENT_COMPLETE`, `SSE_EVENT_SOURCES` |

These are agent-layer event dicts (`{"type": ...}`) and a non-streaming chat
endpoint comparison, not SSE-transport constant definitions. They are
frozen-by-value via the same inventory: any change to the chat constants is
caught by the backend contract test. A future ticket may swap these for the
existing constants; that is out of scope for AE-0076 (Non-Goal: only
literal→existing-constant swaps permitted, and only "at most").

## Contract tests

- **Backend:** `backend/tests/unit/test_sse_event_inventory_contract.py`
  asserts the three backend constant modules match `sse-event-inventory.json`
  exactly; on drift it fails naming the changed constant. Runs under
  `uv run pytest`.
- **Frontend:** `frontend/src/lib/sse-event-inventory.contract.test.ts`
  asserts `EDITORIAL_WORKFLOW_SSE_EVENTS` and `SSE_EVENT_TYPE` match the
  artifact exactly; on drift it fails naming the constant. Runs under
  `npm run test` (Vitest).

Both tests run inside the existing CI quality gates; no new CI workflow files
were added.
