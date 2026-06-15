# Phase 3 — Extract Identity & Conversation boundaries (epic plan)

**Planner output.** Source: `.agent/reports/domain-modularization.options.md` §"Phase 3". Builds on
Phase 2 (PR #16): reuses the AE-0081 module conventions, the `modules/_template`, the Phase-2
`platform/database` Unit of Work, the AE-0093 consumer-owned `KnowledgeSearchPort`, and the
QA-guardian gates. **Precondition: Phase 2 (PR #16) merged.**

## Goal

Extract two bounded contexts — `modules/identity/` (auth/admin/users/roles) and
`modules/conversation/` (chat/messages/streaming) — behind public facades, with routes as thin
adapters and chat-agent construction as an adapter behind conversation contracts. **Behavior-
preserving**: cookies (`access_token`, `anon_token`), HS256 JWT payloads, bcrypt, URLs, SSE event
payloads, keep-alive, `Last-Event-ID`, and `X-Agent-Origin` headers stay byte-identical.

## Reality vs. spec (2026-06-15 code scan)

- **No identity service exists yet** — auth/user logic is split across routes + `api/dependencies/auth.py`
  + `infrastructure/auth.py`. Phase 3 creates `UserService`/`AuthenticationService`.
- **Conversation services exist** (`ConversationService`, `ChatStreamService`); the gap is the **facade**
  + moving **agent construction** (`api/dependencies/agents.py`) behind a `ChatAgentFactory` port.
- **KnowledgeSearchPort already consumer-owned** (AE-0093) and used by agents — that Phase-3 deliverable is done.
- **UoW + repos**: reuse Phase-2 `platform/database` UoW; User/Conversation/Message models are full-field
  (no ORM-repair ticket). Repository ports live in shared `domain/protocols/repositories.py` → re-export shims.
- **`api/middleware/auth.py` + `infrastructure/auth.py` stay at root** (shared token extraction/JWT/bcrypt).
- **`resource_access.py` stays shared** (cross-cutting ownership checks used by 4+ domains) — NOT a new
  module (out of Phase 3 scope; the plan keeps role checks in shared identity contracts). Decision recorded.

## Ticket breakdown

| ID | Title | Tier | Area | Blocked by |
|----|-------|------|------|------------|
| **AE-0096** | Phase 3 epic: Identity & Conversation boundaries | T3 | Cross-cutting | — (tracks 0097-0103) |
| **AE-0097** | Identity + Conversation Gherkin safety nets + response/SSE snapshots | T2 | Tests | — |
| **AE-0098** | `modules/identity/` skeleton + facade + UserService/AuthenticationService + re-exported ports | T2 | Backend | — |
| **AE-0099** | Auth + admin routes behind identity handlers (byte-identical cookies/JWT/bcrypt) | T2 | Backend | AE-0097, AE-0098 |
| **AE-0100** | `modules/conversation/` skeleton + facade + re-exported repo ports + `ChatAgentFactory` port | T2 | Backend | — |
| **AE-0101** | Conversation routes (CRUD + non-streaming chat) behind conversation handlers | T2 | Backend | AE-0097, AE-0100 |
| **AE-0102** | SSE streaming behind conversation via ChatAgentFactory (byte-identical SSE) | T2 | Backend | AE-0101 |
| **AE-0103** | Identity + Conversation import contracts + exit gate + baseline ratchet | T2 | Backend/CI | AE-0099, AE-0102 |

## Suggested order (waves)

- **Wave A (parallel):** AE-0097 (safety nets), AE-0098 (identity skeleton), AE-0100 (conversation skeleton + ChatAgentFactory port).
- **Wave B (parallel):** AE-0099 (identity routes — needs 0097/0098), AE-0101 (conversation routes — needs 0097/0100).
- **Wave C:** AE-0102 (SSE streaming — needs 0101 + the ChatAgentFactory from 0100).
- **Wave D:** AE-0103 (import contracts + exit gate — needs 0099/0102).

## Risks & guardrails

- **Cookie/JWT/bcrypt byte-identical (identity).** Mitigation: AE-0097 snapshots auth responses + cookie attributes; `infrastructure/auth.py` + `api/middleware/auth.py` stay at root, unchanged; AE-0099 gated on snapshot diff=0.
- **SSE payload byte-identical (conversation).** Mitigation: AE-0097 snapshots the SSE event stream (event types, `id:`/`data:` framing, keep-alive ping, `Last-Event-ID`, `X-Agent-Origin`); AE-0102 gated on it. SSE names already frozen (AE-0076).
- **Agent-construction coupling.** `api/dependencies/agents.py` becomes a `ChatAgentFactory` adapter behind conversation/application contracts; must keep AlterEgo/RAG routing (metadata.project_id) + the Phase-2 knowledge facade wiring identical (agent tests).
- **Carousel ↔ conversation coupling** (metadata.project_id, carousel_access.py). Mitigation: keep the link as a UUID in metadata; do not extract carousel here; conversation facade exposes what carousel needs.
- **resource_access shared.** Keep at root; identity re-exports role-check deps via its facade; revisit only if a later phase needs it.
- **No renames** (Phase 4+). UoW reused from platform/database (no new UoW).

## Epic exit gate (from the plan)

- API routes are thin adapters (auth/admin/conversations/chat_stream delegate to facades).
- Conversation application code does not import concrete Postgres repositories (port + facade only).
- Identity persistence is not accessed directly by unrelated routes (via identity facade / shared deps).
- Cookies, tokens, URLs, and SSE/stream payloads byte-identical (AE-0097 snapshots diff=0).
- gates.sh + check-integrity green; import contracts for both modules KEPT.

## Handoff

→ `/architect-skill` validate loop (promote AE-0097-0103 to Ready), then execute Waves A→D with the
developer-skill + QA-guardian loop, as in Phase 2.
