# Phase 2 Plan Validation — architect validate loop

<!-- External cold-critic plan-validation (run_external_qa.sh). Round 1: Cursor — FAIL
(3 blockers V-1/V-2/V-3 + 6 warns). Round 2: OpenCode — PASS. Protocol:
skills/delivery/architect-skill/references/plan-validator.md. Date 2026-06-15. -->

**Verdict: PASS** — AE-0087..0095 validated Ready. Round 1 FAIL → fixes (f596bec) → Round 2 PASS.

## Round 1 findings (Cursor) — all resolved
{
  "verdict": "FAIL",
  "scope": "phase-2-validation",
  "tickets": {
    "AE-0087": "WARN",
    "AE-0088": "WARN",
    "AE-0089": "FAIL",
    "AE-0090": "WARN",
    "AE-0091": "WARN",
    "AE-0092": "WARN",
    "AE-0093": "WARN",
    "AE-0094": "PASS",
    "AE-0095": "WARN"
  },
  "findings": [
    {
      "id": "V-1",
      "severity": "blocker",
      "ticket": "AE-0089",
      "gap": "Delta says relocate domain/protocols/* but knowledge ports live in shared files (repositories.py, ai.py, vector.py) alongside carousel/conversation protocols; ~50+ non-knowledge callers import domain.protocols",
      "fix": "Mandate split+re-export shims at legacy paths; AC: 'import rag_backend.domain.protocols.DocumentRepository unchanged for all existing callers'; only knowledge ports move to modules/knowledge/domain/ports.py"
    },
    {
      "id": "V-2",
      "severity": "blocker",
      "ticket": "AE-0088",
      "gap": "Byte-identical API guarantee (epic, 0092, 0093) has no enforceable baseline \u2014 AC asserts response shape only; no snapshot/golden files; pytest_bdd not in project",
      "fix": "Add AC: capture tests/snapshots/knowledge/{endpoint}.json on green pre-refactor run; 0092/0093 compare against them; name concrete pytest path"
    },
    {
      "id": "V-3",
      "severity": "blocker",
      "ticket": "AE-0092",
      "gap": "AE-0088 listed Related not Blocked-by despite being the safety-net prerequisite; byte-identical AC is unverifiable without 0088 snapshots",
      "fix": "Add Blocked-by: AE-0088; gate merge on snapshot diff = 0"
    },
    {
      "id": "V-4",
      "severity": "warn",
      "ticket": "AE-0095",
      "gap": "Exit gate adds app/domain import bans but not module-conventions \u00a77a knowledge-public-facade contract; agents could reach module internals",
      "fix": "Add knowledge-public-facade forbidden contract (mirror _template stub); AC: agents/api import only rag_backend.modules.knowledge facade"
    },
    {
      "id": "V-5",
      "severity": "warn",
      "ticket": "AE-0091",
      "gap": "UoW + existing get_db() session + route db.commit() risks double-commit; route modification overlaps AE-0092",
      "fix": "AC: UoW wraps request AsyncSession; single commit owner; 0091 delivers UoW primitive, 0092 owns route delegation"
    },
    {
      "id": "V-6",
      "severity": "warn",
      "ticket": "AE-0093",
      "gap": "api/dependencies/agents.py (retriever/document_repo wiring for alter_ego/rag agents) not in delta; Blocked-by missing AE-0088",
      "fix": "Add file to delta; Blocked-by AE-0088; AC naming agent test module"
    },
    {
      "id": "V-7",
      "severity": "warn",
      "ticket": "AE-0088",
      "gap": "Goal claims 20 documents.feature scenarios; repo has 16; scope/is_public scenarios exist in agent_split/document_scope.feature outside ticket scope",
      "fix": "Correct count; decide merge vs cross-reference for scope scenarios to avoid duplication"
    },
    {
      "id": "V-8",
      "severity": "warn",
      "ticket": "AE-0089",
      "gap": "AC claims lint-imports public-facade passes but no knowledge-public-facade contract exists in .importlinter",
      "fix": "Either add contract in 0089 or soften AC to 'no new import violations'; add contract in 0095 per V-4"
    },
    {
      "id": "V-9",
      "severity": "suggestion",
      "ticket": "AE-0090",
      "gap": "No explicit column type/default AC for scope/is_public backfill",
      "fix": "Specify String(20) + server_default='personal'; Boolean NOT NULL server_default=false"
    },
    {
      "id": "V-10",
      "severity": "suggestion",
      "ticket": "AE-0089",
      "gap": "document_pipeline.py and infra adapters (document_repository, hybrid_retriever, pinecone_store) physical relocation not scoped",
      "fix": "Clarify Phase 2 allows bootstrap wiring to global adapters; physical move optional/deferred"
    }
  ]
}
## Round 2 verification (OpenCode)

Let me start by reading the protocol, the plan, and all the ticket files in parallel.
Let me find the actual location of the tickets.
Now let me read all 9 tickets in parallel.
I have read all 9 tickets and the plan document. Let me now verify against the protocol and cross-check the findings systematically.
All files are read. I have everything needed to verify each finding. Here is the full analysis.

---

## Round-2 Plan Validation Report — AE-0087 through AE-0095

### V-1 (blocker, AE-0089 — knowledge-only ports + re-export shims)

**RESOLVED** — evidence:

- **Scope** (line 27): *"Move ONLY the knowledge-specific ports into `modules/knowledge/domain/ports.py` and add **re-export shims at the legacy `domain/protocols/*` paths** so the ~50+ existing non-knowledge callers (agents, carousel, conversation, container) import unchanged."*
- **Scope** (line 28): *"Infrastructure adapters (`document_repository`, `hybrid_retriever`, `pinecone_store`, `openai_embeddings`) and `document_pipeline` are NOT physically relocated in Phase 2"*
- **Scope** (line 29): *"`KnowledgeDocument` re-exports/wraps the existing `Document` entity so `domain/models/documents.py` callers keep working."*
- **Non-Goals** (line 38): *"NO physical relocation of shared infra adapters or shared domain protocol files used by other contexts (re-export/wire instead; physical move is a later phase)."*
- **AC** (line 52): *"WHEN existing callers `import rag_backend.domain.protocols...DocumentRepository/Retriever/etc.` THE imports SHALL keep resolving via re-export shims (no breakage; verified by the full suite)"*

---

### V-2 (blocker, AE-0088 — committed response snapshots + diff helper)

**RESOLVED** — evidence:

- **Scope** (line 28): *"Capture COMMITTED response golden snapshots for each `/api/documents` and `/api/search` endpoint (e.g. `backend/tests/snapshots/knowledge/<endpoint>.json`) on a green pre-refactor run, with a helper to diff live responses against them — this is the enforceable byte-identical baseline that AE-0092/0093 check against."*
- **AC** (line 46): *"THE committed response snapshots (`backend/tests/snapshots/knowledge/*.json`) SHALL be captured for every /api/documents + /api/search endpoint with a diff helper — the enforceable byte-identical baseline AE-0092/0093 check against"*

---

### V-3 (blocker, AE-0092/0093 — Blocked-by AE-0088 + snapshot diff=0)

**RESOLVED** — evidence:

**AE-0092:**
- **Deps** (line 89): *"Blocked by: AE-0088 (snapshot safety net first), AE-0089, AE-0090, AE-0091"*
- **AC** (line 43): *"WHEN any /api/documents endpoint is called THE response SHALL diff to ZERO against the committed AE-0088 snapshots (merge gated on snapshot diff = 0)"*

**AE-0093:**
- **Deps** (line 91): *"Blocked by: AE-0088 (snapshot safety net), AE-0089, AE-0091"*
- **AC** (line 42): *"WHEN /api/search (POST and GET) is called THE response SHALL diff to ZERO against the committed AE-0088 search snapshots"*

---

### V-4 (warn, AE-0095 — knowledge-public-facade Import Linter contract)

**RESOLVED** — evidence:

- **Scope** (line 26): *"ALSO add the knowledge-public-facade contract (mirror module-conventions §7a / `_template`): cross-module callers (agents, api, other modules) import ONLY `rag_backend.modules.knowledge`, not internals."*
- **AC** (line 44): *"THE knowledge-public-facade contract SHALL forbid cross-module imports of knowledge internals (agents/api import only the facade); demonstrated by a reverted internal-import violation"*

---

### V-5 (warn, AE-0091/0092 — UoW single commit owner; route delegation owned by 0092)

**RESOLVED** — evidence:

**AE-0091:**
- **Scope** (line 29): *"This ticket delivers the UoW PRIMITIVE (wrapping the existing request `AsyncSession` as the single commit owner); per-route delegation/commit removal is owned by AE-0092 (avoid double-commit — UoW is the sole committer)."*
- **AC** (line 43): *"WHEN a knowledge write command succeeds THE UoW SHALL commit exactly once at the request boundary"*

**AE-0092:**
- **Scope** (line 27): *"Document writes go through the AE-0091 UoW as the SINGLE commit owner (routes no longer call .commit())."*

No overlap — AE-0091 delivers the primitive, AE-0092 uses it as the single commit owner.

---

### V-6 (warn, AE-0093 — `api/dependencies/agents.py` in delta; Blocked-by AE-0088; agent retrieval test AC)

**RESOLVED** — evidence:

- **Delta MODIFIED** (line 69): *"api/dependencies/agents.py (retriever/document-repo wiring for alter_ego/rag agents → resolve via knowledge facade)"*
- **Deps** (line 91): *"Blocked by: AE-0088 (snapshot safety net), AE-0089, AE-0091"*
- **AC** (line 43): *"THE alter_ego_agent / rag_agent retrieval tests SHALL pass unchanged after redirecting wiring through the facade"*

---

### V-7 (warn, AE-0088 — scenario counts corrected; `document_scope.feature` cross-referenced not duplicated)

**RESOLVED** — evidence:

- **Goal** (line 17): *"Audit and extend the existing `documents.feature` (~16) and `search.feature` (11) Gherkin (and cross-reference the existing `document_scope.feature` rather than duplicating its scope scenarios)"*
- **Scope** (line 29): *"cross-reference (do not duplicate) `document_scope.feature` for scope/access-control coverage"*

The scenario counts are given as approximate ("~16", "11") which is appropriate for a pre-audit ticket. The cross-reference instruction is explicit.

---

### V-8 (warn, AE-0089 — lint-imports AC softened to "no new violations")

**RESOLVED** — evidence:

- **AC** (line 51): *"WHEN `uv run lint-imports` runs THERE SHALL be NO NEW import violations (the dedicated knowledge-public-facade contract is added in AE-0095)"*

This is the correct "no new violations" formulation, explicitly deferring the formal contract to AE-0095. The existing AE-0082 grandfathered violations are not disturbed.

---

### V-9 (sugg, AE-0090 — explicit column types/defaults)

**RESOLVED** — evidence:

- **Scope** (line 26): *"Add an additive Alembic migration (`down_revision = 63eaefa67b8c`): `scope` `String(20)` `server_default='personal'` NOT NULL, `is_public` `Boolean` `server_default=false` NOT NULL (data-preserving backfill)."*

Both column types (`String(20)`, `Boolean`) and defaults (`'personal'`, `false`) are explicitly specified, with NOT NULL + server_default for data-preserving backfill.

---

### Re-Confirmation — overall coverage, dependency graph, no scope creep

| Check | Status | Evidence |
|-------|--------|----------|
| **6 work deliverables covered** | ✅ | AE-0088 (Gherkin), AE-0089 (skeleton), AE-0090 (ORM), AE-0091 (UoW), AE-0092 (routes→handlers), AE-0093 (search), AE-0094 (contract tests), AE-0095 (exit gate). Exit gate encoded in AE-0087 ACs 2-5 + AE-0095 ACs 1-5. |
| **DAG acyclic** | ✅ | `0092←0088/0089/0090/0091`; `0093←0088/0089/0091`; `0094←0089/0090`; `0095←0092/0093`. No cycles. |
| **No scope creep (Phase 4+ items)** | ✅ | All tickets consistently say "no renames", "no new behavior", "no new endpoints". AE-0087 Non-Goals: "No renames of tables/columns/API (Phase 4+). No new product features. No extraction of other contexts." |
| **5-15 testable EARS ACs per ticket** | ✅ | AE-0087: 5, AE-0088: 6, AE-0089: 8, AE-0090: 6, AE-0091: 6, AE-0092: 6, AE-0093: 6, AE-0094: 5, AE-0095: 6. All use `SHALL`/`WHEN` EARS syntax. |
| **No new gaps from edits** | ✅ | No contradictory ACs, no missing dependencies, no orphaned scope items. The AE-0089 "reachable only through facade" design intent aligns with AE-0095's enforcement contract — properly separated. |

---

### JSON Findings Block

```json
{
  "verdict": "PASS",
  "scope": "phase-2-validation-r2",
  "tickets": {
    "AE-0087": "Ready — epic shell covers all sub-tickets + exit gate with 5 EARS ACs",
    "AE-0088": "Ready — response snapshots + diff helper AC present; document_scope.feature cross-reference explicit; scenario counts ~16/11",
    "AE-0089": "Ready — knowledge-only ports move + re-export shims + no shared-infra relocation; AC verifies existing domain.protocols imports keep resolving; lint-imports AC is 'no new violations' deferring facade to AE-0095",
    "AE-0090": "Ready — String(20) default 'personal', Boolean default false with server_default and NOT NULL; additive migration on 63eaefa67b8c; data-preserving backfill",
    "AE-0091": "Ready — UoW primitive as single commit owner; route delegation explicitly owned by AE-0092; no double-commit",
    "AE-0092": "Ready — Blocked-by AE-0088; snapshot diff=0 AC; UoW as single commit owner; no get_container() in handlers",
    "AE-0093": "Ready — api/dependencies/agents.py in delta; Blocked-by AE-0088; agent retrieval test AC; search snapshot diff=0",
    "AE-0094": "Ready — parametrized contract suite vs fake + PostgreSQL; scope/is_public round-trip covered",
    "AE-0095": "Ready — knowledge-public-facade Import Linter contract added; exit gate enforcement + template doc; AE-0082 baseline ratchets down"
  },
  "findings": []
}
```

**QA_VERDICT: PASS**
