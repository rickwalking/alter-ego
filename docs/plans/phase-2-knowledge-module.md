# Phase 2 — Pilot the Knowledge Module (epic plan)

**Planner output** (planner-skill). Source: `.agent/reports/domain-modularization.options.md`
§"Phase 2: Pilot the Knowledge module". Builds on Phase 1 (PR #15): uses the AE-0081
module conventions + `modules/_template/`, the AE-0082 import contracts/ratchet, and the
`bootstrap/` composition root. **Precondition: Phase 1 (PR #15) merged.**

## Goal

Extract documents + search into a real `modules/knowledge/` bounded context — domain,
application (command/query handlers + ports), infrastructure adapters, behind a single
public facade — with a request-scoped Unit of Work. **Behavior-preserving**: `/api/documents`
and `/api/search` stay byte-identical (no renames — that's Phase 4+). This is the pilot that
proves the reusable module template.

## Reality vs. the original spec (from a 2026-06-15 code scan)

- **Gherkin already exists** (`tests/features/documents.feature` 20 scenarios, `search.feature`
  11). The spec's "write them first — none exist" is stale → **audit & extend** them as the
  safety net (scope/access-control gaps) instead of writing from scratch.
- **Domain models + all 5 protocols already exist** in `domain/` (`Document`, `DocumentChunk`,
  `SearchResult`, `RetrievalQuery`; `DocumentRepository`, `VectorStore`, `EmbeddingService`,
  `Retriever`, `DocumentProcessor`). Phase 2 relocates/organizes them into the module.
- **Real ORM gap**: `Document` entity has `scope` + `is_public`; `DocumentModel` and the
  (AE-0086 squashed) baseline do **not** persist them → additive migration required.
- **No request-scoped UoW**; routes call `get_container()` + `await db.commit()` directly.
- **Conversation/agent search** goes through `build_search_documents_tool(retriever)` (LangChain
  tool), not direct calls — redirect it through the knowledge facade.

## Ticket breakdown (vertical slices, one ≈ one branch)

| ID | Title | Tier | Area | Blocked by |
|----|-------|------|------|------------|
| **AE-0087** | Phase 2 epic: Knowledge module pilot | T3 | Cross-cutting | — (tracks 0088-0095) |
| **AE-0088** | Document + search Gherkin safety net (audit & extend) | T2 | Tests | — |
| **AE-0089** | `modules/knowledge/` skeleton + ports + public facade (KnowledgeDocument, commands/queries) | T2 | Backend | — |
| **AE-0090** | Repair full-field ORM mapping (`scope`/`is_public`) + additive migration | T2 | Backend/DB | — |
| **AE-0091** | Request-scoped Unit of Work | T2 | Backend | AE-0089 |
| **AE-0092** | Move document routes behind application handlers (facade) | T2 | Backend | AE-0089, AE-0090, AE-0091 |
| **AE-0093** | Move search behind the module + redirect conversation/agent search via facade | T2 | Backend | AE-0089, AE-0091 |
| **AE-0094** | Fake + PostgreSQL repository contract tests | T2 | Tests | AE-0089, AE-0090 |
| **AE-0095** | Knowledge import contract + exit-gate enforcement + reusable-template doc | T2 | Backend/CI | AE-0092, AE-0093 |

## Suggested order (waves)

- **Wave A (parallel, disjoint):** AE-0088 (Gherkin safety net), AE-0089 (module skeleton+ports), AE-0090 (ORM repair + migration).
- **Wave B:** AE-0091 (UoW — needs the module).
- **Wave C (parallel):** AE-0092 (document handlers — needs 0089/0090/0091) + AE-0094 (repo contract tests — needs 0089/0090).
- **Wave D:** AE-0093 (search + conversation/agent redirect — needs 0089/0091).
- **Wave E:** AE-0095 (import contract + exit gate — needs the module's app layer clean, i.e. after 0092/0093).

## Risks & guardrails

- **Behavior drift while relocating.** Mitigation: the AE-0088 Gherkin safety net must pass at every step; `/api/documents` + `/api/search` responses byte-identical (extend the route-snapshot or add response contract assertions); no renames.
- **ORM-repair migration vs AE-0086 baseline.** `scope`/`is_public` added as an **additive** migration on top of the squashed baseline `63eaefa67b8c` (new revision, `down_revision=63eaefa67b8c`); must keep AE-0084's empty-autogenerate-diff drift check green. Additive nullable columns — no drain/migrate-in-place ceremony needed (pre-production, not a reshape; F1/F3 risk-register items are Phase 4+).
- **Import-contract tightening.** AE-0095 adds a knowledge-module contract on top of AE-0082; existing global violations stay grandfathered, the new module's application layer must be clean (no SQLAlchemy/FastAPI/Pinecone/`get_container`).
- **Agent/search coupling.** The `search_documents_tool` + agents must resolve search via the knowledge facade without changing agent behavior; covered by the search Gherkin.
- **UoW scope creep.** Introduce the UoW request-scoped for knowledge writes only (pilot); do not refactor the whole app's session handling (later phases).

## Epic exit gate (from the plan)

- No knowledge **application** code imports SQLAlchemy, FastAPI, Pinecone, or the global container (AE-0095 contract enforces).
- The document/search Gherkin scenarios pass (AE-0088 safety net green throughout).
- The module template is documented and reusable (AE-0095) — proving the pattern for Phases 3-8.
- `/api/documents` + `/api/search` unchanged; full suite + Phase-1 ratchets green.

## Handoff

→ `/architect-skill` validate loop (promote AE-0088-0095 to Ready; sharpen ACs), then execute
Waves A→E with the developer-skill + external QA loop, as in Phases 0/1.
