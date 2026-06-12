# Alter-Ego Domain Modularization Research

**Mode:** architect-skill research
**Date:** 2026-06-11
**Scope:** Backend, frontend, persistence, API, agents, workflows, tests, and architecture controls
**Decision status:** Research only; no production code changed
**ADR required:** Yes

## Executive Summary

Alter-Ego should evolve from a global package-by-layer structure into a
domain-module-first modular monolith. Each bounded context should own its
domain language, application use cases, ports, adapters, and public contracts.
The existing FastAPI process, PostgreSQL database, Next.js application, URLs,
and user-visible behavior can remain in place during the migration.

The highest-impact modeling issue is the meaning of `CarouselProject`.
It currently represents all of these concepts at once:

- An editorial project and creative brief
- A seven-phase human review workflow
- Research source ownership
- A carousel presentation and its slides
- Design tokens, images, PDFs, and artifact paths
- A blog representation
- Instagram and LinkedIn copy
- Public visibility and publication state
- Ownership, reviewer assignment, persona, and rubric selection

This is not a cohesive carousel aggregate. A carousel should mean the
presentation artifact and its production rules. The broader lifecycle should
be modeled as an `EditorialProject`, with separate bounded contexts for
workflow, presentation, quality, publishing, knowledge, conversation, and
identity.

The migration is medium-high difficulty, but it does not require a rewrite.
The first useful boundary can be introduced in 1-2 weeks. Completing the
highest-value modularization is approximately 8-14 engineer-weeks for one
senior engineer, or 5-8 calendar weeks for two engineers with carefully
separated work.

## Research Method

The investigation included:

1. Project rules in `CLAUDE.md`, backend/frontend guidance, and agent rules.
2. All accepted ADRs, especially ADR-002, ADR-003, ADR-004, ADR-006, and
   ADR-007.
3. Backend package inventory, import relationships, DI composition, ORM
   models, repositories, protocols, routes, workflows, and tests.
4. Frontend route groups, atomic components, feature folders, API contracts,
   schemas, hooks, and vocabulary.
5. Existing refactor plans and tasks, including AE-0040 through AE-0069.
6. Four parallel read-only research threads:
   - Backend domains and current carousel ownership
   - Frontend language and feature boundaries
   - Persistence, DI, transactions, tests, and architecture gates
   - External DDD, modular monolith, ports/adapters, and frontend guidance
7. Primary and authoritative external sources listed at the end of this
   report.

## Quantified Baseline

| Measure | Current size |
|---|---:|
| Backend Python source files | 363 |
| Backend source lines | 43,807 |
| Frontend TypeScript/TSX files | 406 |
| Frontend source lines | 41,638 |
| Backend test files | 139 |
| Frontend test files | 75 |
| Alembic migration files | 11 |
| Import Linter files analyzed | 355 |
| Import Linter dependencies analyzed | 1,307 |

> **Correction (2026-06-12 verification):** the frontend figures above did
> not reproduce. A re-measurement found ~305 non-test TS/TSX files and
> ~25,700 non-test lines under `frontend/src`. Backend figures reproduce
> within normal drift (367 files; carousel services 12,405 lines). The
> frontend baseline must be re-measured with a documented methodology
> (Phase 0 deliverable in the options report) before estimates are
> re-confirmed.

The carousel/editorial surface is already a large subsystem:

| Area | Lines |
|---|---:|
| `application/services/carousel` | 11,893 |
| `application/services/carousel_template` | 2,737 |
| Carousel API routes | 2,688 |
| Carousel-named agent modules | 827 |
| Frontend create/carousel/publish/blog/workflow features | 15,036 |
| Carousel/editorial/presentation backend test files | 57 |

> **Correction (2026-06-12 verification):** the 15,036-line figure for the
> five frontend features did not reproduce; non-test lines measure roughly
> 6,100 (create 2,093, blog 2,064, publish 1,077, workflow 752, carousel
> 133). The `carousel` feature folder is a thin query layer only.

`CarouselProject` or its persistence/API vocabulary appears in 69 backend
source files and carousel API vocabulary appears in 55 frontend files. This
is too broad for a direct rename or move.

## Current Architecture

### Intended structure

The written architecture is global Clean Architecture:

```text
domain -> application -> infrastructure -> api
```

The intended rule is that dependencies point inward. Protocols should isolate
application and domain logic from FastAPI, SQLAlchemy, external vendors, and
agent runtimes.

### Actual structure

The codebase is a layered monolith whose business capabilities cut across all
global layers:

```text
api/
application/
domain/
infrastructure/
agents/
```

Adding a capability usually requires touching several global folders. The
folders express implementation categories more strongly than business
ownership.

Observed import relationships include:

| Relationship | Import lines |
|---|---:|
| Application -> infrastructure | 58 |
| Infrastructure -> application | 13 |
| Application -> agents | 20 |
| Agents -> application | 19 |
| Agents -> infrastructure | 15 |
| API -> infrastructure | 96 |
| API -> agents | 9 |

File-level scans found:

- 37 application files importing infrastructure.
- 22 application files importing SQLAlchemy or `AsyncSession`.
- 15 application files importing agents.
- 8 agent files importing application.
- 41 API files importing infrastructure.

### Architecture gate weakness

`backend/.importlinter` declares that application cannot import
infrastructure, but then ignores:

```text
rag_backend.application.** -> rag_backend.infrastructure.**
rag_backend.application.** -> rag_backend.agents.**
```

Therefore `uv run lint-imports` reports four passing contracts while the most
important dependency violations are globally exempted. The gate confirms the
configuration, not the intended architecture.

### Composition and service location

`infrastructure/container.py` acts as a global container and imports agents,
application services, repositories, and vendors. A composition root may
depend on all modules, but the current container is located inside
`infrastructure` and is also accessed from application services as a service
locator.

Composition is also duplicated in:

- `api/app.py`, which initializes vendors, database, workers, checkpointers,
  middleware, health checks, and routes.
- `api/dependencies/agents.py`, which reconstructs request-scoped agent graphs.
- Application services that call `get_container()` directly.

### Persistence and transaction ownership

Transaction responsibility is inconsistent:

- Some repositories flush and expect callers to commit.
- Some repositories commit internally.
- API routes and application services also commit.

This makes multi-repository use cases and cross-context operations difficult to
reason about.

The event flow is also non-atomic in places. Workflow events can be published
to Redis before the PostgreSQL audit record is persisted. A Redis success and
database rollback can leave the external event stream inconsistent with the
authoritative state.

### API routes as transaction scripts

Several route modules perform all of these jobs directly:

- Query ORM models
- Apply business rules
- Mutate records
- Publish events
- Write audit data
- Commit transactions
- Build transport responses

This is especially visible in blog posts, sources, workflow board, identity,
and parts of carousel routes. These use cases need application handlers, not
additional route helper files.

### Agents as an ambiguous layer

The top-level `agents/` folder mixes:

- Domain-specific orchestration
- LangGraph and DeepAgents runtime code
- Prompt loading
- Infrastructure cache and telemetry access
- Database repositories
- Application services

Agents import application and infrastructure, while application imports
agents. This creates a bidirectional dependency. Agents should become inbound
or outbound adapters inside an owning context, depending on their role:

- A chat assistant is an inbound interaction adapter.
- A model invocation is an outbound `TextGenerator` adapter.
- A LangGraph workflow is an application process manager or orchestration
  adapter, not a separate architectural layer.

## Carousel Definition

### Current definition

The current `CarouselProject` domain model contains:

- Carousel metadata and slides
- Blog markdown and translations
- Instagram caption
- LinkedIn posts
- Design and image generation settings
- Workflow phase and progress
- Persona and rubric references
- Public visibility
- Creator branding
- Artifact and PDF paths

The ORM adds reviewer assignment, workflow status, and a `lock_version`
column. **Verification note (2026-06-12):** `lock_version` exists since
migration 0002 but no application code enforces it — optimistic locking is
declared, not implemented. Any expected-version contract must first build
the enforcement.

The separate `BlogPostModel` also references `carousel_projects`, which
creates two blog representations with unclear authority. The frontend
mirrors the ambiguity: two different hooks are both named `useBlogPosts()`
(`features/blog/hooks/use-carousel-blog.ts` fetches completed carousel
projects; `use-blog-posts.ts` manages first-class blog posts), and the
public `/blog` route renders carousel projects.

### Recommended definition

Use the following language:

| Concept | Definition |
|---|---|
| `EditorialProject` | The aggregate coordinating a brief, owner, sources, selected formats, and editorial lifecycle. |
| `EditorialWorkflow` | The phase/review process for one editorial project. |
| `CarouselPresentation` | A format-specific artifact composed of ordered slides and presentation policy. |
| `CarouselSlide` | One localized presentation unit within a carousel presentation. |
| `ArtifactBuild` | A reproducible build of rendered images/PDFs from presentation inputs. |
| `BlogPost` | A first-class long-form publication aggregate. |
| `ChannelPublication` | A release to a public channel, with visibility and scheduling. |
| `DistributionCopy` | Caption, LinkedIn text, hashtags, and other channel-specific copy. |
| `SourceMaterial` | User-provided or selected input for an editorial project. |
| `ResearchSource` | Evidence collected during research, with provenance and relevance. |
| `MessageCitation` | Evidence attached to a conversation response. |

Under this model, carousel does not own:

- Blog bodies or SEO
- Editorial assignments and workflow state
- Persona or rubric definitions
- Public visibility or schedules
- Notifications, audit records, or analytics
- Generic chat and RAG behavior

### Compatibility rule

Do not immediately rename:

- Database tables
- Existing URLs
- Existing SSE payload fields
- Existing external response schemas

Instead, introduce a legacy anti-corruption adapter:

```text
Legacy CarouselProject row/API
        |
        v
EditorialProject + CarouselPresentation + DistributionPackage
```

The adapter translates old persistence and transport shapes into the new
module contracts. One write authority must remain in place until a later data
migration.

## Domain and Subdomain Map

The product domain is **AI-assisted editorial production and publishing**.

### Core subdomains

| Bounded context | Owns |
|---|---|
| Editorial Production | Editorial projects, briefs, source materials, phase lifecycle, human review, assignments, revisions, approvals, and project-level orchestration. |
| Carousel Presentation | Slides, localized presentation copy, layout strategies, design tokens, image prompts, rendering, validation, artifact builds, and PDF export. |
| Persona and Quality | Persona profiles, writing style, corrections, voice enforcement, quality rubrics, evaluations, and thresholds. |

### Supporting subdomains

| Bounded context | Owns |
|---|---|
| Publishing and Distribution | Blog publication, public visibility, scheduling, channel releases, Instagram publishing, LinkedIn copy, captions, SEO, and publication projections. |
| Knowledge and Retrieval | Documents, scopes, ingestion, chunking, indexing, retrieval, and search. |
| Conversation | Conversations, messages, anonymous sessions, streaming interaction, and citations. |
| Editorial Operations | Notifications, calendar, workflow board, audit queries, analytics, and administrative projections. |

### Generic subdomains and platform

| Area | Owns |
|---|---|
| Identity and Access | Users, credentials, roles, sessions, authentication, and authorization policy. |
| Platform | Settings, database engine/session, logging, tracing, cache, Redis transport, vendor SDK clients, file storage, and process startup. |

These boundaries are hypotheses until validated against use cases and business
language. They should be refined with a short event-storming/context-mapping
workshop before physical moves.

## Context Relationships

Recommended high-level context map:

```text
Identity and Access
        |
        v
Editorial Production -----> Persona and Quality
        |                           |
        |                           v
        +-----> Knowledge and Retrieval
        |
        +-----> Carousel Presentation
        |
        +-----> Publishing and Distribution
        |
        +-----> Editorial Operations (projections/events)

Conversation -----> Knowledge and Retrieval
Conversation -----> Editorial Production public facade
```

Rules:

1. Ordinary in-process queries may use synchronous public module interfaces.
2. Cross-context workflow notifications should use integration events when
   temporal decoupling is valuable.
3. Write transactions should not span bounded contexts.
4. Read models may compose data from multiple contexts without importing their
   domain internals.
5. Ports are defined by the consuming module.
6. Cross-module imports go through `public.py` or `contracts/`, never internal
   domain/application/adapter packages.

## Recommended Backend Structure

```text
rag_backend/
  bootstrap/
    app.py
    container.py
    lifecycle.py
    routes.py

  modules/
    identity/
      domain/
      application/
      ports/
      adapters/
        inbound/http/
        outbound/persistence/
      contracts/
      public.py
      bootstrap.py

    knowledge/
      domain/
      application/
      ports/
      adapters/
        inbound/http/
        outbound/persistence/
        outbound/retrieval/
      contracts/
      public.py
      bootstrap.py

    conversation/
    editorial/
    carousel_presentation/
    persona_quality/
    publishing/
    editorial_operations/

  platform/
    config/
    database/
    events/
    observability/
    cache/
    ai/
    storage/

  legacy/
    carousel_project/
      acl.py
      api_compat.py
      persistence_compat.py
```

Not every module needs every subfolder. Small modules should stay small.
Create `domain`, `application`, `ports`, or `adapters` only when the module has
code that belongs there.

### Internal dependency direction

```text
adapters/inbound -> application -> domain
adapters/outbound implements application/domain ports
bootstrap composes all parts
```

The application layer must not import:

- FastAPI
- SQLAlchemy
- `infrastructure` or `platform` implementations
- LangChain/LangGraph vendor types
- OpenAI, Anthropic, Pinecone, Redis, or Playwright SDK types
- The global container

## Recommended Frontend Structure

Keep the Next.js App Router and atomic design. Change business ownership, not
the rendering model:

```text
frontend/src/
  app/                         # Routes and composition only

  modules/
    identity/
    knowledge/
    conversation/
    editorial/
      workspace/
      workflow/
      sources/
    carousel-presentation/
      preview/
      review/
      refinement/
    persona-quality/
    publishing/
      blog/
      distribution/
      scheduling/
    editorial-operations/

  components/
    atoms/                     # Domain-neutral only
    molecules/                 # Domain-neutral only
    organisms/                 # Domain-neutral shell/layout only
    layout/
    providers/

  platform/
    api/
    query/
    i18n/
    telemetry/
```

An incremental alternative is to retain the `features/` folder name while
changing its children to the same bounded-context names. The name of the root
folder matters less than clear ownership and enforced public APIs.

Specific frontend corrections:

- `create` is a user journey, not a domain. Move it under `editorial/workspace`.
- Consolidate `persona` and `personas`.
- Move dashboard adapters into their actual owning modules.
- Reserve `BlogPost` for the first-class blog aggregate.
- Rename carousel-derived public content to `CarouselArticle` or another
  explicit projection.
- Keep business-specific cards and boards out of global atomic components.
- Co-locate each module's Zod DTOs, API client, query keys, hooks, and adapters.
- Use OpenAPI as an executable transport contract and check generated or
  validated frontend schemas in CI.

## Ubiquitous Language Gaps

| Current term | Problem | Recommended term |
|---|---|---|
| `project` | Usually means carousel project, but sounds generic | `EditorialProject` internally; qualified IDs externally |
| `carousel project` | Owns non-carousel workflow and publications | Compatibility term only |
| `create` | Route/action used as feature name | `EditorialWorkspace` |
| `workflow` | Means carousel phases, blog state, and board | `EditorialWorkflow`, `BlogReviewLifecycle`, `WorkflowBoardProjection` |
| `status` | Generation, review, publication, and failures mixed | `build_status`, `phase_status`, `review_status`, `publication_status` |
| `blog` | Carousel article and independent blog post | `CarouselArticle` vs `BlogPost` |
| `source` | User input, research result, or chat citation | `SourceMaterial`, `ResearchSource`, `MessageCitation` |
| `publish` | Approval and public release conflated | `approve` vs `release` |
| `agent` | Domain worker and vendor runtime mixed | `Orchestrator`, `Generator`, `Evaluator`, or `Assistant` |
| `admin` | UI role/surface treated as domain | Identity use cases plus admin adapter |

## Ports and Design Patterns

Introduce patterns only where they remove coupling.

### High-value ports

- `UnitOfWork`
- `EditorialProjectRepository`
- `CarouselPresentationRepository`
- `BlogPostRepository`
- `KnowledgeDocumentRepository`
- `TextGenerator`
- `EmbeddingIndex`
- `ResearchProvider`
- `ArtifactStore`
- `ImageGenerator`
- `PdfRenderer`
- `EventPublisher`
- `TraceSink`
- `Clock`

### High-value patterns

| Pattern | Use |
|---|---|
| Repository | Hide persistence details from application/domain code. |
| Unit of Work | Make transaction ownership explicit at the use-case boundary. |
| Application handler | Replace route transaction scripts with named commands/queries. |
| Strategy | Format-specific layout, rendering, model selection, and publication channel behavior. |
| Builder | Complex artifact or response assembly with stable required steps. |
| Anti-corruption layer | Translate legacy `CarouselProject` rows and APIs into new module models. |
| Outbox | Atomically persist integration events with state changes. |
| Process manager | Coordinate long-running workflows across aggregates/contexts. |
| Read model/projector | Build boards, calendars, analytics, and public lists without cross-context domain joins. |

Avoid introducing:

- A generic repository base class
- A global event bus for every local function call
- A command bus solely to replace normal Python calls
- One interface per class
- A shared-kernel dumping ground
- Separate deployable services before module boundaries are proven

## Testing and Fitness Functions

### Backend

1. Replace broad Import Linter ignores with exact temporary exceptions.
2. Ratchet exception counts downward in CI.
3. Forbid module internals from being imported outside the module.
4. Forbid application imports of SQLAlchemy, FastAPI, agents, vendor SDKs, and
   platform implementations.
5. Forbid `get_container()` outside bootstrap/inbound dependency providers.
6. Forbid `.commit()` inside repository adapters.
7. Add cycle checks between sibling modules.
8. Add repository contract tests against fake and SQLAlchemy adapters.
9. Add full-field domain/ORM round-trip tests.
10. Run fresh PostgreSQL migration tests with `alembic upgrade head`.
11. Fail CI if production startup uses `metadata.create_all()`.
12. Restore strict mypy coverage one module at a time.

### Frontend

1. Add ESLint boundary rules for module public APIs.
2. Prevent feature/module internals from cross-importing.
3. Keep `app/` as the only route composition layer.
4. Keep atomic components domain-neutral.
5. Validate transport responses with module-owned Zod schemas.
6. Check OpenAPI/schema drift in CI.
7. Preserve Gherkin scenarios as behavior-level migration protection.

## Difficulty and Risk

**Overall difficulty:** Medium-high, approximately 7/10.

Why it is not a simple folder move:

- The carousel/editorial surface is about 18,000 backend lines plus 15,000
  frontend lines.
- Domain, application, agents, ORM, API, and frontend contracts are coupled.
- Existing URLs, SSE streams, checkpoints, database rows, and public content
  must continue working.
- Blog content currently has two potential sources of truth.
- Transaction and event ownership are not consistent.
- Current architecture gates mask significant violations.
- Existing AE-0040 refactor tasks are modifying some of the same files.

Why it is still feasible incrementally:

- The system remains a single deployable backend and frontend.
- Protocols, repositories, ADRs, Gherkin tests, and Import Linter already exist.
- Knowledge, conversation, identity, and carousel concepts have recognizable
  clusters.
- FastAPI routers and Next.js route composition support gradual redirection.
- Existing API shapes can be retained through compatibility adapters.

## Primary Risks

1. **Big-bang moves:** High probability of import churn and hidden behavior
   regressions.
2. **Premature context boundaries:** Splitting carousel, blog, and workflow
   without first defining use cases can formalize accidental coupling.
3. **Dual writes:** Writing old and new models without one authority can
   produce divergence.
4. **Checkpoint compatibility:** Renaming LangGraph nodes/state can strand
   in-flight workflows.
5. **Visibility regression:** Approval and public release must remain separate.
6. **Event inconsistency:** Redis publication must not precede the
   authoritative transaction.
7. **Concurrent refactors:** AE-0040 tasks overlap carousel and frontend files.
8. **Over-engineering:** Applying full tactical DDD to CRUD/generic contexts
   would add ceremony without value.

## ADR Check

An ADR is required because this changes:

- Module ownership
- Dependency direction
- Composition root placement
- Transaction ownership
- Event publication policy
- Public module contracts
- Backend and frontend ubiquitous language
- Architecture enforcement

Proposed ADR:

```text
docs/decisions/0009-adopt-domain-modular-monolith.md
```

The ADR should be drafted only after the recommended option and initial
context map are accepted.

## External Sources

- [Microsoft: Domain analysis and ubiquitous language](https://learn.microsoft.com/en-us/azure/architecture/microservices/model/domain-analysis)
- [Microsoft: Identify boundaries from bounded contexts and aggregates](https://learn.microsoft.com/en-us/azure/architecture/microservices/model/microservice-boundaries)
- [Microsoft: Tactical DDD](https://learn.microsoft.com/en-us/azure/architecture/microservices/model/tactical-domain-driven-design)
- [DDD Crew: Context Mapping](https://github.com/ddd-crew/context-mapping)
- [DDD Crew: Bounded Context Canvas](https://github.com/ddd-crew/bounded-context-canvas)
- [Alistair Cockburn: Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Cosmic Python: Repository pattern](https://www.cosmicpython.com/book/chapter_02_repository.html)
- [Cosmic Python: Unit of Work](https://www.cosmicpython.com/book/chapter_06_uow.html)
- [Microsoft: Anti-Corruption Layer](https://learn.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer)
- [Martin Fowler: Strangler Fig modernization](https://martinfowler.com/bliki/OriginalStranglerFigApplication.html)
- [FastAPI: Bigger applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Import Linter contract types](https://import-linter.readthedocs.io/en/stable/contract_types/)
- [Next.js project structure and route groups](https://nextjs.org/docs/app/getting-started/project-structure)
- [Feature-Sliced Design migration](https://feature-sliced.design/docs/guides/migration/from-custom)
- [Modular Monolith with DDD reference implementation](https://github.com/kgrzybek/modular-monolith-with-ddd)
- [Bulletproof React project structure](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md)
