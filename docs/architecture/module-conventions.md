# Module Conventions — Bounded-Context Public API

**Status:** Accepted (Phase 1 scaffolding deliverable)
**Owner ticket:** AE-0081
**Date:** 2026-06-12
**Applies to:** every bounded-context module under
`backend/src/rag_backend/modules/`

This document defines how a bounded-context module is laid out, how it exposes
its **public API**, where the **Unit-of-Work boundary** sits, and how those
rules map to the **Import Linter contract shape** that AE-0082 enforces. It is
the convention Phase 2+ modules copy from the reference template at
`backend/src/rag_backend/modules/_template/`.

It is normative for module structure. It does **not** move behavior, change
schemas, or rename code (Phase 1 is scaffolding only — see ADR-0009 §1–2 and
the AE-0081 ticket Non-Goals).

## Cross-links

- [ADR-0009: Adopt Domain Modular Monolith](../decisions/0009-adopt-domain-modular-monolith.md)
  — DI is manual constructor injection (§9); authorization is context-owned
  and deny-by-default (§5); single-writer discipline (§6).
- [Domain Glossary and Context Map](./domain-glossary.md) (AE-0071) — the
  canonical context names used below.
- Reference template: `backend/src/rag_backend/modules/_template/`.
- Import contracts (to be authored): **AE-0082** — consumes the contract
  shape and minimum stub in this document.

---

## 1. Bounded contexts (naming)

Every module name SHALL be one of the nine glossary contexts (AE-0071,
Context Map). New documentation and code use the canonical context name; the
glossary's compatibility terms (`carousel_projects`, `/api/carousels/*`,
`CarouselProject`, `blog_markdown`) are not module names.

| Module package | Glossary context | Classification |
|---|---|---|
| `editorial` | `editorial` | Core |
| `carousel_presentation` | `carousel_presentation` | Core |
| `persona` | `persona` | Core (differentiator) |
| `quality` | `quality` | Core (differentiator) |
| `publishing` | `publishing` | Supporting |
| `knowledge` | `knowledge` | Supporting |
| `conversation` | `conversation` | Supporting |
| `editorial_operations` | `editorial_operations` | Supporting (full module) |
| `identity` | `identity` | Generic |
| `platform` | `platform` | Technical |

Notes:

- `persona` and `quality` are **two** modules; `quality` depends on `persona`
  (dependency direction quality → persona), never the reverse (ADR-0009 §4,
  glossary persona→quality note).
- `identity` and `platform` are distinct modules (glossary row 9). `platform`
  is the technical substrate that supplies `PlatformServices` to every
  module's `bootstrap_module()`; it lives at `rag_backend.platform`, not under
  `modules/`.
- `_template` is the reference skeleton, not a real context. Its
  leading-underscore name keeps it out of any glob over real modules.

---

## 2. Per-module internal layout

Each module is a self-contained package with its own internal layers (the
global `domain/application/infrastructure/api` split, re-applied **inside** the
module). The reference template demonstrates exactly this shape:

```
modules/<context>/
├── __init__.py          # re-exports the public facade (the public API)
├── public.py            # PUBLIC FACADE — the only legal cross-module import
├── bootstrap.py         # composition root: bootstrap_module(platform)
├── constants.py         # module-owned constants (no magic strings)
├── domain/              # entities, value objects, ports (Protocols) — innermost
│   ├── models.py
│   └── ports.py
├── application/         # use cases / services; owns the Unit-of-Work boundary
│   └── service.py
├── infrastructure/      # adapters implementing domain ports (DB, clients)
│   └── repository.py
└── api/                 # inbound adapters (HTTP/agent/worker) + boundary DTOs
    └── views.py
```

Layer dependency direction inside a module mirrors Clean Architecture:
`domain` ← `application` ← `infrastructure` / `api`. The domain layer imports
nothing outward; application depends only on domain (its ports); infrastructure
and api wire concrete adapters. Adapters are constructed in `bootstrap.py`, not
imported by domain/application (dependency inversion).

---

## 3. The public-facade rule

This is the central convention.

> **Cross-module imports SHALL go only through a module's public API — its
> `public.py` (re-exported from the package `__init__`). Everything else under
> `modules/<context>/` is private to that module.**

Concretely:

- A module's **public API** is the set of symbols in `public.py` /
  `__init__.__all__`. These are typically: the application service(s) that are
  the use-case entry points, boundary-safe **view/command DTOs**, and
  `bootstrap_module`.
- **Allowed** (facade import):

  ```python
  from rag_backend.modules.persona import PersonaService, VoiceScoreView
  ```

- **Forbidden** (reaching into internals):

  ```python
  from rag_backend.modules.persona.application.service import PersonaService
  from rag_backend.modules.persona.domain.models import VoiceScore
  ```

- Domain **entities** are never exposed across the boundary; expose a view DTO
  (see `api/views.py` in the template) so consumers depend on a stable shape,
  not the module's internals.
- A module SHALL NOT import another module's `domain`, `application`,
  `infrastructure`, or `api` subpackages directly — only the other module's
  facade.

The reference template exemplifies this: its own internals import sibling
internals freely (e.g. `application.service` imports `domain.ports` and
`api.views`), but the only path a *consumer* uses is
`rag_backend.modules._template` / `.public`.

---

## 4. Unit-of-Work boundary placement

The **Unit-of-Work boundary is owned at the application layer** and scoped to
one inbound request/command:

- The request-scoped Unit of Work is **created at the inbound edge** (the `api`
  layer adapter — FastAPI `Depends` at the HTTP edge; explicit construction in
  workers and agent adapters) and **passed into the application service** as a
  constructor or call argument. It is never resolved from a global container
  (ADR-0009 §9).
- The application service performs its use case within that single UoW and
  commits once at the boundary; infrastructure adapters enlist in it.
- A command that affects only this context commits within this module's UoW.
  While `carousel_projects` remains shared persistence, cross-context writes
  are coordinated through the **single legacy Unit of Work / sole writer**
  (ADR-0009 §6) — a module returns decisions/results to the legacy coordinator
  rather than writing the shared row itself. Independent module write ownership
  begins only after the relevant fields move to module-owned persistence.

The template omits the concrete UoW object to avoid coupling to the
not-yet-built `platform` plumbing; its `bootstrap.py` and docstrings mark
where a real module injects it.

---

## 5. Dependency injection / composition root

Per ADR-0009 §9, wiring is **manual constructor injection — no DI framework**:

- `bootstrap_module(platform: PlatformServices)` is the module's composition
  root. It receives the shared platform services, constructs the module's
  infrastructure adapters, injects them into application services, and returns
  the public service(s).
- Test doubles are swapped by calling `bootstrap_module` (or constructing the
  service) with fake ports — no container patching.

The template defines a local `PlatformServices` Protocol placeholder; a real
module imports `rag_backend.platform.PlatformServices` once it exists.

---

## 6. Authorization at inbound adapters

Per ADR-0009 §5, every inbound adapter (HTTP route, **agent tool**,
**worker**, event consumer) SHALL supply an `ActorContext` and call the
**context-owned, deny-by-default** authorization policy before invoking the
application service. Authorization is owned by the module that owns the
resource, not centrally by `identity`. The template's `api/__init__.py`
documents this seam; the policy itself arrives with each real module.

---

## 7. Import Linter contract shape (input for AE-0082)

AE-0082 finalizes `backend/.importlinter`. This section states the **shape** of
the contracts it will add; this ticket does not modify `.importlinter`
(Non-Goal).

The current file already enforces the *global* layer contracts
(`domain-independence`, `application-independence`,
`infrastructure-independence`, `domain-acyclic`). AE-0082 adds **module
boundary** contracts on top, expressed with Import Linter's standard contract
types:

### 7a. Public-facade contract (`forbidden`, one per module)

For each module, forbid every other module from importing its private
internals; only the facade module is reachable. Each module's internal
subpackages (`domain`, `application`, `infrastructure`, `api`, `bootstrap`,
`constants`) are the forbidden targets; the facade (`modules.<context>` /
`modules.<context>.public`) stays allowed because it is not listed.

```ini
[importlinter:contract:<context>-public-facade]
name = <context> internals are private (import via the facade only)
type = forbidden
source_modules =
    rag_backend            # every other module / layer
forbidden_modules =
    rag_backend.modules.<context>.domain
    rag_backend.modules.<context>.application
    rag_backend.modules.<context>.infrastructure
    rag_backend.modules.<context>.api
    rag_backend.modules.<context>.bootstrap
    rag_backend.modules.<context>.constants
ignore_imports =
    # the module's own facade may import its internals
    rag_backend.modules.<context>.public -> rag_backend.modules.<context>.**
    rag_backend.modules.<context>.__init__ -> rag_backend.modules.<context>.**
    # the module's own internals may import each other
    rag_backend.modules.<context>.** -> rag_backend.modules.<context>.**
```

> Implementation note for AE-0082: an `independence`/`layers` contract over the
> set of module facades is the cleaner long-term encoding once ≥2 real modules
> exist (it also captures the quality → persona one-way rule). The `forbidden`
> shape above is the minimum that enforces the facade rule for a single module
> and is what the stub in §7c uses.

### 7b. Per-module internal layering (`layers`, optional but recommended)

Each module re-applies the Clean-Architecture order internally:

```ini
[importlinter:contract:<context>-internal-layers]
name = <context> internal layers are acyclic and inward-only
type = layers
containers =
    rag_backend.modules.<context>
layers =
    api
    infrastructure
    application
    domain
```

### 7c. Minimum stub AE-0082 references (resolves the 0081→0082 ordering)

AE-0082 can write its first real contract against the reference template
**before** any real module exists, using the symbols this ticket shipped. This
stub is verified green by AE-0081 (`uv run lint-imports` passes with the
template in place):

```ini
[importlinter:contract:template-public-facade]
name = _template internals are private (import via the facade only)
type = forbidden
source_modules =
    rag_backend.api
    rag_backend.application
    rag_backend.domain
    rag_backend.infrastructure
forbidden_modules =
    rag_backend.modules._template.domain
    rag_backend.modules._template.application
    rag_backend.modules._template.infrastructure
    rag_backend.modules._template.api
    rag_backend.modules._template.bootstrap
    rag_backend.modules._template.constants
```

This stub holds today: nothing outside the template reaches into its
internals, and the template's own facade (`public.py` / `__init__`) is the
only public entry point. When AE-0082 lands, real modules replace `_template`
with their context name following §7a.

### 7d. Application/domain exit-gate contract (`forbidden`, one per module) — AE-0095

A real module's **inner layers** (`application`, `domain`) SHALL stay free of
frameworks, vendor SDKs, and the global DI container. Modules live under
`rag_backend.modules.<context>`, which is **outside** `rag_backend.application`,
so the global `application-no-infrastructure` contract does **not** cover them —
each module needs its own exit-gate contract:

```ini
[importlinter:contract:<context>-application-isolation]
name = <context> application/domain must not import frameworks, vendors, or the global container
type = forbidden
allow_indirect_imports = true
unmatched_ignore_imports_alerting = none
source_modules =
    rag_backend.modules.<context>.application
    rag_backend.modules.<context>.domain
forbidden_modules =
    sqlalchemy
    fastapi
    pinecone
    rag_backend.infrastructure.container
```

Notes:

- The top-level `[importlinter]` block sets `include_external_packages = true`
  so external forbidden targets (`sqlalchemy`, `fastapi`, `pinecone`) are in the
  graph. This is required by Import Linter whenever any contract forbids an
  external package; it leaves every internal-only contract unaffected (all stay
  KEPT).
- `allow_indirect_imports = true` keeps this a **per-edge** gate: only a *direct*
  forbidden import in the module's inner layers breaks it. Indirect chains
  (`application -> ... -> infrastructure.container`) are owned by their own
  direct-edge contracts.
- A clean module (the goal) carries **no `ignore_imports`** here — any new
  framework/vendor/container import in the inner layers breaks CI immediately.

---

## 8. Checklist for a new module

1. Copy `modules/_template/` to `modules/<context>/` (a glossary context name).
2. Replace the template entity/port/service/view with the real aggregate and
   use cases; keep the layer dirs and the `public.py` facade.
3. Export only boundary-safe symbols from `public.py` / `__init__.__all__`.
4. Create the request-scoped UoW at the inbound (`api`) edge; inject it into
   services.
5. Wire adapters in `bootstrap_module(platform)` (manual constructor
   injection).
6. Supply `ActorContext` and call the context-owned authorization policy in
   every inbound adapter.
7. Add the §7a public-facade contract, the §7d application/domain exit-gate
   contract (and optionally §7b layers) to `.importlinter`. Author them in the
   generator `scripts/metrics/import_baseline.py` (`render_importlinter`) so
   `--emit-importlinter` regeneration stays stable, then regenerate the file.
8. Verify: `MYPYPATH=src uv run mypy -p rag_backend`,
   `uv run ruff check src/rag_backend/modules/`, `uv run lint-imports`,
   `uv run python ../scripts/metrics/import_baseline.py --check`,
   `uv run pytest`.

---

## 9. Worked example — the `knowledge` module (reusable Phase-2 template)

The **`knowledge`** bounded context is the first real module to complete the
full convention end-to-end (Phases 2a–2d: AE-0089/0092/0093/0095). It is the
proven pattern Phases 3–8 copy verbatim. Source:
`backend/src/rag_backend/modules/knowledge/`.

### 9a. Layout (matches §2 exactly)

```
modules/knowledge/
├── __init__.py            # re-exports public.py (the public API)
├── public.py              # PUBLIC FACADE — KnowledgeService, commands/queries,
│                          #   view DTOs, KnowledgeSearchPort, bootstrap_module
├── bootstrap.py           # bootstrap_module(...) -> KnowledgeAdapters (manual DI)
├── constants.py
├── domain/                # models.py, ports.py, commands.py (no outward imports)
├── application/           # service.py (use cases + UoW boundary), search_port.py
├── infrastructure/        # adapters implementing domain ports
└── api/                   # views.py — boundary-safe DTOs
```

### 9b. Facade in practice (§3)

Cross-module callers import **only** the facade — verified across the agent and
API edges:

```python
# agents/rag_agent.py, agents/alter_ego_agent.py, api/routes/search.py,
# api/dependencies/{agents,knowledge}.py, application/tools/knowledge_base/...
from rag_backend.modules.knowledge import KnowledgeService, KnowledgeSearchPort, SearchQuery
```

The `KnowledgeSearchPort` (in `application/search_port.py`, re-exported from the
facade) is the boundary-safe hybrid-search contract: inbound adapters depend on
it instead of wiring a raw retriever that would bypass the module.

### 9c. The two enforcing contracts (§7a + §7d)

`backend/.importlinter` carries both knowledge contracts, generated from
`render_importlinter` in `scripts/metrics/import_baseline.py`:

- **`knowledge-application-isolation`** (§7d) — `application`/`domain` forbidden
  from importing `sqlalchemy`, `fastapi`, `pinecone`, and
  `infrastructure.container`. The inner layers are clean, so it carries **no
  `ignore_imports`**: a new framework/vendor/container import fails CI at once.
- **`knowledge-public-facade`** (§7a) — `api`/`agents`/`application`/`domain`/
  `infrastructure` forbidden from importing knowledge internals
  (`domain`/`application`/`infrastructure`/`api`/`bootstrap`/`constants`). The
  one legacy internal edge (`api.routes.documents -> domain.commands` for the
  `MetadataValue` type) is grandfathered via `ignore_imports`; everything else
  goes through the facade.

Both use `allow_indirect_imports = true` (per-edge gate) and
`unmatched_ignore_imports_alerting = none` (robust against grimp graph
granularity differences without weakening enforcement — a NEW edge still
breaks).

### 9d. Ratchet effect (AE-0082 baseline)

Routing the agent/route edges through the facade and dropping the global
container from the module path **ratcheted the AE-0082 baseline DOWN**
(`api -> infrastructure` and `get_container()` locator counts both fell);
`import_baseline.py --check` stays PASS because counts may only decrease. Later
phases inherit this: every module they extract cleanly lowers the ceilings
further, never raises them.

### 9e. Copy this for Phases 3–8

For each new module: add a `<context>-public-facade` (§7a) and a
`<context>-application-isolation` (§7d) contract to `render_importlinter`,
regenerate `.importlinter`, and confirm both are KEPT with no (or only
explicitly grandfathered) ignores — the knowledge contracts are the literal
template.

## 10. Worked examples — the `identity` & `conversation` modules (Phase 3)

Phase 3 (AE-0096–0103) applied the §9 template twice more, behavior-preserving
(byte-identical cookies, HS256 JWT, bcrypt, SSE event payloads/framing/keep-alive/
`Last-Event-ID`/`X-Agent-Origin`):

### 10a. `identity` (auth/admin/users/roles)
- **Layout** (§2): `modules/identity/{domain,application,infrastructure,api}` +
  `public.py` + `bootstrap.py` + `constants.py`.
- **Services** (AE-0098): `UserService` / `AuthenticationService` / `PasswordService`
  in the application layer — they **delegate all JWT/bcrypt to the unchanged
  `infrastructure/auth.py`** (the single crypto source) rather than reimplementing it.
- **Shims**: `UserRepository` port + `User`/`UserRole` are **re-exported** from the
  shared `domain/protocols` / `domain/models` (object identity preserved — ~50
  callers unbroken), exactly as knowledge did.
- **Routes** (AE-0099): `auth.py` + `admin.py` are thin adapters delegating to the
  facade via the `get_identity_service` DI edge; they no longer import
  `get_container` / a concrete user repository or call `db.commit()` (the platform
  UoW is the single committer).
- `api/middleware/auth.py`, `infrastructure/auth.py`, and
  `api/dependencies/resource_access.py` deliberately **stay at root** — shared,
  cross-domain authz; `resource_access.py`'s `UserModel` import is a recorded,
  grandfathered exception (out of Phase 3 scope to relocate), not a gate hole.

### 10b. `conversation` (chat/messages/streaming)
- **Layout** (§2) + facade, as above.
- **`ChatAgentFactory` port** (AE-0100): chat-agent construction becomes an adapter
  behind a conversation/application contract; `LegacyChatAgentFactory` wraps the
  existing `build_alter_ego_agent` / `build_rag_agent` with identical
  `metadata.project_id` → AlterEgo/RAG routing and knowledge-facade wiring.
- **Routes** (AE-0101) + **SSE streaming** (AE-0102) delegate via the facade; the
  streaming application layer (`application/streaming.py`) imports only ports — no
  concrete Postgres repository, no `get_container`. The SSE wire is still owned by
  the unchanged `stream_chat_response`; a module-level `build_alter_ego_agent`
  seam in `api/routes/chat_stream.py` is preserved so the byte-identical safety
  net can substitute a deterministic mock agent.

### 10c. The four enforcing contracts (§7a + §7d) — AE-0103
`backend/.importlinter` now carries, generated from `render_importlinter`:
`identity-application-isolation`, `identity-public-facade`,
`conversation-application-isolation`, `conversation-public-facade`. Both modules
are clean → **no `ignore_imports`** on any of the four; a NEW framework/container/
infrastructure import in an inner layer, or a NEW cross-module import of an
internal, breaks CI (demonstrated and reverted during AE-0103).

### 10d. Ratchet effect (AE-0082 baseline) — AE-0103
Moving the auth/admin/conversation/chat-stream edges behind the facades ratcheted
the baseline **down again**: `api -> infrastructure` 98 → 82 and the
`get_container()` locator count 26 → 14. `import_baseline.py --check` stays PASS
(counts may only decrease).

## 11. Worked example — the `editorial` module (Phase 4: a god-object slice + ACL)

Phase 4 (AE-0104–0113) extracted the **workflow slice** of the legacy `CarouselProject`
god object into `modules/editorial/`, behavior-preserving (carousel workflow API + SSE
byte-identical; LangGraph checkpoints + `lock_version` semantics stable). It is the
template for extracting a slice of a shared, multi-writer aggregate behind an
**anti-corruption layer (ACL)** rather than a clean-owned table.

### 11a. Field-ownership map first (AE-0105)
Before redirecting any write, `docs/architecture/carousel-project-field-ownership.md`
maps every `carousel_projects` column → invariant, current writer(s), owning context,
and concurrency token, separating workflow-owned (WO) from deferred columns and flagging
multi-writer columns. Extracting a slice of a god row **requires** this map.

### 11b. Single write owner + ACL (AE-0107 / AE-0109)
- `CarouselProjectWriteOwner` (editorial/infrastructure) is the sole writer of the WO
  columns; legacy routes/services route their WO writes through it and it commits via the
  platform UoW. The `lock_version` resume CAS delegates unchanged to `OptimisticLockService`;
  the artifact-activation CAS pairing is untouched.
- `LegacyCarouselAcl` (editorial/infrastructure) is the **only** editorial code importing
  the carousel ORM — it translates the legacy row ↔ `EditorialProject`/`EditorialWorkflow`.
  Editorial `application`/`domain` import no ORM.
- **DDD-layer note:** the owner/ACL live in `modules/editorial/infrastructure` (not the
  global `application` layer) precisely so they may import the carousel ORM without an
  `application→infrastructure` violation; legacy callers reach them through the editorial
  **public facade** (`application/api → modules.editorial`, not a tracked `→infrastructure`
  edge). ORM-write typing was fixed by migrating the WO columns to SQLAlchemy 2.0
  `Mapped[...]` — never a mypy override.

### 11c. Deferred boundary (documented, not gamed)
The terminal-finalization write (`editorial_finalize` → `repo.update_project`) persists WO
`status`/`error_message` **atomically** with deferred Phase-5 presentation columns in one
commit; splitting it would break that atomicity, so it stays on the legacy W1 persistence
path — recorded as an explicit Non-Goal in AE-0107 + a code comment. Preserving
byte-identical atomicity outranks mechanical "single-owner" purity.

### 11d. Approval ≠ public release (AE-0111)
Approval (`workflow_status → approved_for_publish`) and public release (`is_public`) are
distinct editorial ports/value objects — a contract split, not a visibility-behavior change.

### 11e. The two enforcing contracts + ratchet (AE-0112)
`editorial-application-isolation` (§7d) + `editorial-public-facade` (§7a), generated by
`render_importlinter`, zero `ignore_imports` (both clean; violations demonstrated+reverted).
`api -> infrastructure` ratcheted 82 → 81 (editorial workflow routes behind the facade).

### 11f. Checkpoint-drain rule (exit-gate criterion)
Phase 4 keeps LangGraph checkpoint identifiers (`thread_id = project_id`) and the
`CarouselWorkflowState` schema stable, so **no** schema-modifying migration was needed.
The exit gate mandates: **no schema-modifying migration may run while a live LangGraph
checkpoint references the old shape** — every live checkpoint must first be finished on the
pre-migration code or restarted with documented owner consent (ADR-0009 round-4 findings).
Later phases that change the carousel/editorial schema MUST satisfy this drain before migrating.

## 12. Worked example — the `presentation` module (Phase 5: god-object slice #2 + cross-module port)

Phase 5 (AE-0114–0122) extracted the carousel PRESENTATION slice (slides, design/theming, layout
strategies, policy/validation/review, rendering, image generation + providers, artifact build/
activation, export, creator assets) into `modules/presentation/`, behavior-preserving (presentation
response schemas + artifact URLs + `FileResponse` bytes/headers + the `artifact_version`↔`lock_version`
activation CAS byte-identical). It is the template for a SECOND slice of the same god row plus a clean
**module→module port** to the already-extracted editorial context.

### 12a. Surface map first (AE-0115)
`docs/architecture/presentation-surface-ownership.md` (extends AE-0105) maps the presentation
`carousel_projects` columns + the `CarouselSlideModel` rows to writers, classifies presentation-owned
vs deferred (distribution → Phase 6), and documents the shared `artifact_version`↔`lock_version` CAS.

### 12b. Single write owner + ACL + the shared CAS (AE-0118)
`PresentationWriteOwner` / `PresentationPersistenceAcl` (presentation/infrastructure) are the only
presentation code importing the carousel/slide ORM. The `artifact_version`↔`lock_version` activation
CAS is SHARED with the editorial AE-0107 owner (resume CAS) — both delegate to the same unchanged
primitive; a no-clobber concurrency test proves activate_build vs editorial-resume interleave with
exactly-one-wins. ORM-write typing uses SQLAlchemy 2.0 `Mapped[...]`, never a mypy override.

### 12c. Vendor adapters behind ports (AE-0119)
Image generation goes through `ImageProviderPort`/`ImageGenerationService`; OpenAI/Gemini are adapters
with the vendor SDK imports confined to `infrastructure/external`. Presentation application/domain
depend only on the port.

### 12d. Routes + the editorial→presentation port (AE-0120 / AE-0121)
Presentation routes (media/preview/slides/strategies/admin/creator-assets) are thin adapters over the
facade (`api/dependencies/presentation.py`). The editorial workflow invokes presentation via the public
facade (artifact build, design/images/export, policy/validation/review) — **editorial → presentation
only**. The `nodes/images.py` `phase_progress` write became a **presentation→editorial callback port**
(the `WorkflowProgressPort` Protocol is owned by presentation; the editorial side implements + injects
it), so the dependency direction stays acyclic with no module cycle. `ContentFormatProducer` is a
presentation-specific extension point (one `CarouselFormatProducer`; no generic framework yet).

### 12e. The three enforcing contracts + ratchet (AE-0122)
`presentation-application-isolation` (§7d) + `presentation-public-facade` (§7a) + **`presentation-no-
editorial`** (the acyclic-direction contract), generated by `render_importlinter`, zero `ignore_imports`
(all clean; violations demonstrated + reverted). The presentation ACL is the only allowed carousel/slide-
ORM importer. Baseline ratcheted: `api -> infrastructure` 81 → 79 (presentation routes behind the facade)
and `agents -> application` 20 → 19 (carousel_workflow_nodes review-edits via the facade port).

### 12f. Checkpoint-drain rule (re-affirmed)
As in §11f: no schema-modifying migration may run while a live LangGraph checkpoint references the old
shape. Phase 5 needed no migration; the rule remains an exit-gate criterion for later carousel/editorial/
presentation schema changes.

## 13. Worked example — the `publishing` module (Phase 6: behavior-preserving + additive publish/blog/distribution)

Phase 6 (AE-0123..0132) extracted the carousel/blog **publish + distribution + read-model** slice into
`modules/publishing/`, **behavior-preserving and additive-only** (the carousel publish/release flow, the
standalone blog publish/unpublish/schedule routes, the Instagram distribution + caption read, and the
public carousel `/blog`, content-calendar, workflow-board, and editorial-analytics read surfaces all stay
byte-identical). It is the template for a slice that is **invoked BY** the already-extracted editorial and
presentation contexts (publishing is downstream of approval), and for landing the additive halves of a
larger exit gate while explicitly deferring its behavior-changing / destructive halves.

### 13a. Two ACL/owner seams — writes and reads (AE-0128 / AE-0131)
The publishing context **accesses** (queries / mutates) the legacy carousel/blog ORM through **exactly two**
infrastructure modules — the only publishing code that touches the database for it. (A third infrastructure
module, `read_projection_helpers.py`, is a stateless markdown helper the read ACL delegates body extraction
to; it imports the `BlogPostModel` *type* only to annotate the row the ACL hands it and performs no ORM access
of its own.) The two ACL seams:
- **`legacy_publishing_acl.py`** (the WRITE owner) backs `CarouselReleasePort` (the `is_public=True` /
  `current_phase=published` public-release write, byte-identical to `crud.py:publish_carousel`, committed
  once via the platform UoW), `BlogVisibilityPort` (publish/unpublish status writes, flush-only — the route
  owns the event + commit), and `BlogSchedulePort` (the schedule write + the due-post sweep, delegating
  unchanged to `ScheduledPublishService`).
- **`publishing_read_acl.py`** (the READ owner) backs `PublishingReadPort` (the carousel-blog projection,
  content-calendar, workflow-board, editorial-analytics) and `BlogPostCrudPort` (the blog-post persistence
  rows). Every method returns a boundary-safe projection value object — never the ORM, never `Any`.

The publishing `application`/`domain` layers depend only on these ports (plus the platform UoW and other
facades); they import no carousel/blog ORM directly. As in §11b/§12b the owner/ACL live in
`modules/publishing/infrastructure` precisely so they may import the ORM without an
`application→infrastructure` violation, and callers reach them through the publishing **public facade**.

### 13b. Object-identity re-export shims (AE-0126 constraint) — the one documented isolation exception
`domain/ports.py` re-exports `CarouselRepository` (from `rag_backend.domain.protocols.repositories`) and
`BlogPostRepository`, and `domain/models.py` re-exports `BlogPostModel` (both from
`rag_backend.infrastructure.database…`). Physically relocating those definitions would break the carousel
routes / workflow engine / blog routes that still import the legacy paths, so this phase **re-exports**
them in place — the legacy import paths keep resolving to the IDENTICAL objects, mirroring
`modules.editorial.domain.ports` / `modules.presentation.domain.ports`. Because `BlogPostRepository` and
`BlogPostModel` live under `rag_backend.infrastructure`, the two re-export edges
(`publishing.domain.ports → infrastructure.database.blog_post_repository` and
`publishing.domain.models → infrastructure.database.models.blog_post`) are the **only two
`ignore_imports` across all module isolation gates** — an explicit, documented exception in
`render_importlinter`. Every OTHER carousel/blog-ORM import in publishing must go through the two ACL
modules above; any NEW infrastructure import in the inner layers breaks CI.

### 13c. Additive migration + transactional outbox (AE-0127 / AE-0130)
- **AE-0127** adds `BlogPost.origin` and **backfills** `origin='carousel'` rows for carousel blogs — purely
  ADDITIVE (a new column + a backfill; **no embedded carousel column is dropped**). The carousel-blog read
  projection reads the backfill row when present and falls back **per-field** to the embedded carousel
  columns (`blog_markdown` / `title or topic` / `subtitle`), and the 404 gate still keys on the EXACT legacy
  `blog_markdown is None` signal, so the response is byte-identical and a backfill row can never flip a
  legacy 404 into a 200.
- **AE-0130** adds a transactional **outbox** ALONGSIDE the existing after-commit publish (additive — the
  legacy publish path is unchanged); the outbox row is staged in the same transaction as the state write so
  delivery is idempotent and at-least-once without changing observed behavior.

### 13d. Read-model projections (AE-0131)
The public/editor READ surfaces are served by `PublishingReadPort` projections (`CarouselBlogProjection`,
`CalendarProjection`, `BoardProjection`, `AnalyticsProjection`) that replicate the legacy `media.py` blog
routes, `ContentCalendarService`, the `workflow_board` route, and `EditorialAnalyticsService`
field-for-field. The thin HTTP routes map each projection one-to-one onto the existing response schemas.

### 13e. The three enforcing contracts + ratchet (AE-0132)
`publishing-application-isolation` (§7d) + `publishing-public-facade` (§7a) + **`publishing-no-editorial-
presentation`** (the acyclic-direction contract — publishing is invoked BY editorial/presentation via the
facade, so it must import neither's internals), generated by `render_importlinter`. The isolation contract
carries the only two `ignore_imports` (the §13b re-export shims); the other two are clean. All three were
demonstrated by a reverted violation. Baseline ratcheted: `application -> infrastructure` 63 → 62 and
`api -> infrastructure` 79 → 76 (blog/publish/distribution/board/calendar/analytics reads + writes moved
behind the publishing facade/ACL). Total contracts 19 → 22.

### 13f. Checkpoint-drain rule (re-affirmed)
As in §11f / §12f: no schema-modifying migration may run while a live LangGraph checkpoint references the
old shape. **Phase 6's migration is additive (AE-0127: add `origin` + backfill, no drop) ⇒ no drain was
needed.** The rule remains the binding exit-gate criterion for the deferred destructive drop (§13g).

### 13g. Deferred, consent-gated exit-gate halves — tracked by AE-0133
The *full* roadmap Phase-6 exit gate also names two items that are **behavior-changing / destructive**, so
they are deliberately deferred out of this behind-facade phase and tracked as a post-Phase-6, consent-gated
follow-up in **AE-0133** (Intake):
1. **Auto-publish behavior cutover.** Editorial approval and public release become two **distinct user
   actions** (approval never auto-publishes). The approval≠release *contract* is already split (AE-0111,
   §11d) and the publishing release command exists; the actual behavior cutover needs the **Phase-7
   frontend** and is a real behavior change — so its safety net must be updated to assert the NEW behavior,
   under explicit owner consent. Not done here.
2. **Destructive embedded-column drop.** A migration dropping the embedded carousel
   `blog_markdown` / `blog_translations` / `caption*` / `linkedin_post_*` columns from `carousel_projects`,
   **gated by the §13f checkpoint-drain rule** (every live LangGraph checkpoint finished on pre-migration
   code or restarted with documented consent) AND by `blog_posts` being the confirmed single writer (no
   remaining embedded-column writers), once the migration window has elapsed. The AE-0111 contract split and
   the AE-0127 additive backfill are already in place; only the destructive drop remains. Not done here.

Landing the additive halves now (behind the import contracts) while deferring the behavior-changing /
destructive halves to a consent-gated ticket is the deliberate Phase-6 strategy — additive isolation first,
cutover and destructive cleanup later with owner consent.
