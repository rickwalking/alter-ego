# Domain Glossary and Context Map

**Status:** Accepted (Phase 0 deliverable for the domain modularization plan)
**Owner ticket:** AE-0071
**Date:** 2026-06-12
**Format:** grill-with-docs — one canonical term per concept; rejected
synonyms listed under an **_Avoid_** entry.

This is the single ubiquitous-language reference shared by backend,
frontend, tests, API schemas, events, and documentation. Every term has
exactly one canonical definition and exactly one owning bounded context.

## Scope and authority

- This document **defines language and the context map**. It does not
  define architecture policy or rename anything in code, database, or API.
- Modeling decisions are **transcribed** from the implementation interview
  (`.agent/reports/domain-modularization.interview.md`, 2026-06-12), not
  re-decided here.
- Architecture policy (rollback track, authorization, outbox, operating
  context) is decided in **ADR-0009** (drafted concurrently in AE-0072):
  `docs/decisions/0009-adopt-domain-modular-monolith.md`.
- The context classifications and charters are reconciled against the
  "Proposed Contexts" table in
  `.agent/reports/domain-modularization.options.md`, as amended by the
  interview (persona/quality split into two; editorial_operations is a full
  module).

### Cross-links

- Options and recommended plan:
  [`.agent/reports/domain-modularization.options.md`](../../.agent/reports/domain-modularization.options.md)
  (see "Proposed Contexts", "Interview Decisions", "Phased Migration Plan").
- ADR-0009 (eventual path, drafted in AE-0072):
  [`docs/decisions/0009-adopt-domain-modular-monolith.md`](../decisions/0009-adopt-domain-modular-monolith.md).
- Interview record (authoritative source for terms and checkpoint
  decisions):
  [`.agent/reports/domain-modularization.interview.md`](../../.agent/reports/domain-modularization.interview.md).

## Compatibility note (read before using this glossary)

This glossary is **target language**. Per the ticket Non-Goals, **no code,
database, or API renames happen as part of AE-0071**. Existing identifiers
(`carousel_projects`, `/api/carousels/*`, `CarouselProject`, `blog_markdown`,
the `useBlogPosts()` collision) remain in place until the relevant migration
phase. Where a legacy alias still exists in the running system, the glossary
marks it **"compatibility term only"** and names its replacement. Using the
canonical term in new docs/code does not authorize a rename.

---

## Context Map

The accepted architecture is a **domain-module-first modular monolith**
(Option B) with **nine bounded contexts**. Names are reconciled against the
options report; the interview split the report's single `persona_quality`
row into two contexts (`persona`, `quality`) and elevated
`editorial_operations` from a read-side projection to a full module.

| # | Context | Classification | One-line charter |
|---|---|---|---|
| 1 | `editorial` | **Core** | Owns the `EditorialProject` aggregate: brief, source material, workflow lifecycle, review, assignment, revision, and approval; produces formats as outputs. |
| 2 | `carousel_presentation` | **Core** | Owns `CarouselPresentation`: slides, layout, design, images, validation, rendering, and artifact builds. |
| 3 | `persona` | **Core (differentiator)** | Owns persona profiles, corrections, `VoiceScore`, and `PersonaAgent.enforce()`; exposes voice-match measurement through a public contract. |
| 4 | `quality` | **Core (differentiator)** | Owns quality rubrics and evaluation; **consumes** `VoiceScore` via persona's public contract (dependency direction: quality → persona). |
| 5 | `publishing` | **Supporting** | Owns `BlogPost`, `ChannelPublication`, `DistributionCopy`, public visibility, scheduling, and channel delivery (Instagram, LinkedIn, captions, SEO). |
| 6 | `knowledge` | **Supporting** | Owns `KnowledgeDocument`, `ResearchSource`, ingestion, chunks, indexing, retrieval, and search. |
| 7 | `conversation` | **Supporting** | Owns `Conversation`, `Message`, chat streaming, `MessageCitation`, and assistant interaction. |
| 8 | `editorial_operations` | **Supporting** (full module) | Owns notification dispatch and board/calendar behavior as real owned behavior from day one; its views are event-built read models, never direct joins into other contexts' tables. |
| 9 | `identity` / `platform` | `identity`: **Generic** · `platform`: **Technical** | `identity` owns users, roles, sessions, credentials, authentication, and authorization. `platform` owns the technical substrate: database engine, settings, Redis transport, logging, tracing, cache, vendors, file storage. |

Notes:

- Row 9 pairs the two non-business contexts the plan lists separately
  (`identity` Generic, `platform` Technical). They are distinct modules; they
  share one row only to keep the count at the nine **business-and-platform**
  contexts named in the plan.
- **persona → quality dependency:** `quality` depends on `persona`. Persona
  is the sole owner of `VoiceScore` and enforcement; quality reads the score
  through persona's contract and never reaches into persona internals.
- `editorial_operations` builds **read models from other contexts' events**,
  not from cross-context table joins.

---

## Glossary

Each entry: canonical term — one-line definition (owning context).

### Core aggregates and project language

#### EditorialProject
The aggregate owning a piece of work end to end: brief, sources, workflow
lifecycle, owner/reviewer; produces formats (carousel, blog) as outputs.
**Owning context:** `editorial`.
**_Avoid:_**
- `CarouselProject` — **compatibility term only**; the live `carousel_projects`
  table and `/api/carousels/*` routes keep this name until migrated.
  Replacement: **EditorialProject**.
- `ContentProject` — rejected (interview decision 3).
- `Campaign` — rejected (interview decision 3).
- `carousel project` (prose alias) — **compatibility term only**; replacement:
  **EditorialProject**.

#### EditorialWorkflow
The workflow lifecycle of an `EditorialProject` — phase transitions,
review gates, approval — modeled as the editorial context's workflow
language over the underlying LangGraph execution.
**Owning context:** `editorial`.
**_Avoid:_** bare `Workflow` as a standalone domain noun outside this context
(it is overloaded with LangGraph execution mechanics); use
**EditorialWorkflow** for the business lifecycle.

### Carousel presentation

#### CarouselPresentation
The presentation aggregate for a carousel: its slides, layout, design,
images, validation, and rendering. "Carousel" means **presentation only**
in target language — not the project, not the article.
**Owning context:** `carousel_presentation`.

#### CarouselSlide
A single slide within a `CarouselPresentation` (copy + design + image
references for one frame).
**Owning context:** `carousel_presentation`.

#### ArtifactBuild
A produced, versioned rendering output of a `CarouselPresentation` (e.g., a
rendered image set / export), tracked with build identity and version.
**Owning context:** `carousel_presentation`.
**_Avoid:_** conflating an `ArtifactBuild` (the render output) with
`CarouselPresentation` (the editable presentation) — they are distinct.

### Publishing and distribution

#### BlogPost
The **single** long-form publication aggregate, backed by `blog_posts`,
carrying `origin: carousel | standalone` and linked to an `EditorialProject`.
There is exactly one blog representation; carousel-derived long-form content
is a `BlogPost` with `origin = carousel`, not a separate type.
**Owning context:** `publishing`.
**_Avoid:_**
- `CarouselArticle` — **rejected** (interview decision; no second blog
  representation survives). Replacement: **BlogPost** with `origin = carousel`.
  See the naming-collision appendix for the evidence.
- `blog_markdown`-as-source-of-truth — **compatibility term only**; the
  embedded carousel `blog_markdown`/translation columns remain a compatibility
  projection until Phase 6 migrates them into `blog_posts` rows and drops the
  embedded columns. Replacement: **BlogPost** (`origin = carousel`).

#### ChannelPublication
A publication of content to a specific channel (e.g., the public blog,
Instagram, LinkedIn), including its visibility and scheduling state. This is
the canonical sense of "Publication".
**Owning context:** `publishing`.
**_Avoid:_** using bare `Publication` to mean editorial approval — approval
(`review_status`) is separate from publication (`publication_status`).

#### DistributionCopy
Channel-specific derived copy for a `ChannelPublication` — captions, SEO
text, per-platform variants generated for distribution.
**Owning context:** `publishing`.

### Knowledge and conversation

#### SourceMaterial
Brief- or project-scoped input material attached to an `EditorialProject`
that feeds content production (the editorial-side notion of "source").
**Owning context:** `editorial`.
**_Avoid:_** using bare `Source` to mean both editorial input material and a
researched knowledge reference — those are **SourceMaterial** (editorial) and
**ResearchSource** (knowledge), respectively.

#### ResearchSource
A retrieved/ingested knowledge reference (document, chunk, or external
reference) owned by the knowledge context and used for retrieval and citation.
**Owning context:** `knowledge`.

#### MessageCitation
A citation attached to a conversation `Message`, linking assistant output to
its supporting `ResearchSource`.
**Owning context:** `conversation`.

### Persona and quality

#### VoiceScore
The persona-owned voice-match measure (gate: **≥ 70** before human review).
Persona owns the score and `PersonaAgent.enforce()`; quality consumes it
through persona's public contract.
**Owning context:** `persona`.
**_Avoid:_** `persona_quality` as the owner — superseded by the interview
decision to split persona and quality into two contexts. Replacement: the
**`persona`** context owns `VoiceScore`.

### Status families

The four status families are **distinct dimensions**; do not collapse them
into one overloaded `status` field.

#### build_status
The lifecycle state of an `ArtifactBuild` (e.g., pending / building /
succeeded / failed).
**Owning context:** `carousel_presentation`.

#### phase_status
The state of a phase/transition within an `EditorialWorkflow`.
**Owning context:** `editorial`.

#### review_status
The state of editorial review / approval for an `EditorialProject`
(approval is **not** publication).
**Owning context:** `editorial`.

#### publication_status
The state of a `ChannelPublication` (e.g., draft / scheduled / published /
unpublished). Distinct from `review_status`.
**Owning context:** `publishing`.

### Cross-cutting _Avoid_ summary

| Avoid term | Status | Use instead |
|---|---|---|
| `CarouselProject` | Compatibility term only (live in code/DB/API) | `EditorialProject` |
| `carousel project` (prose) | Compatibility term only | `EditorialProject` |
| `ContentProject` | Rejected | `EditorialProject` |
| `Campaign` | Rejected | `EditorialProject` |
| `CarouselArticle` | Rejected | `BlogPost` (`origin = carousel`) |
| `persona_quality` | Superseded | `persona` and `quality` (two contexts) |
| `blog_markdown` as source of truth | Compatibility term only | `BlogPost` (`origin = carousel`) |
| bare `status` | Overloaded | one of `build_status` / `phase_status` / `review_status` / `publication_status` |
| bare `Source` | Overloaded | `SourceMaterial` (editorial) or `ResearchSource` (knowledge) |
| bare `Publication` for approval | Overloaded | `review_status` (approval) vs `ChannelPublication` (publish) |

---

## Single-definition guarantee

The following terms required by the ticket each resolve to **exactly one**
definition (no term defined twice):

| Term | Canonical meaning | Owning context |
|---|---|---|
| `Carousel` | `CarouselPresentation` (presentation only) | `carousel_presentation` |
| `EditorialProject` | The core project aggregate | `editorial` |
| `BlogPost` | The single long-form publication aggregate (`origin: carousel \| standalone`) | `publishing` |
| `Publication` | `ChannelPublication` (channel publish, not approval) | `publishing` |
| `Workflow` | `EditorialWorkflow` (business lifecycle) | `editorial` |
| `Source` | Disambiguated: `SourceMaterial` (editorial) / `ResearchSource` (knowledge) | `editorial` / `knowledge` |
| `build_status` | `ArtifactBuild` lifecycle state | `carousel_presentation` |
| `phase_status` | `EditorialWorkflow` phase state | `editorial` |
| `review_status` | Editorial review/approval state | `editorial` |
| `publication_status` | `ChannelPublication` state | `publishing` |

---

## Human Checkpoint decisions

Transcribed from `.agent/reports/domain-modularization.interview.md`
(2026-06-12, protocol: grill-with-docs; interviewee: Pedro Marins, owner).
These are **recorded, not re-decided**.

The plan's Human Checkpoint posed **six** questions. **Question 6 (operating
context — users, traffic, in-flight LangGraph checkpoints, tenancy) is
decided in ADR-0009 (AE-0072), not here.** The five modeling questions below
are recorded in this glossary.

| # | Question | Decision | Rationale (from interview) |
|---|---|---|---|
| 1 | Is the broader aggregate `EditorialProject`, `ContentProject`, or `Campaign`? | **EditorialProject** | Recommended option accepted; names the project by its editorial nature without the marketing connotation of `Campaign` or the vagueness of `ContentProject`. |
| 2 | Is carousel-derived long-form content a `CarouselArticle`, a `BlogPost`, or only a publishing projection? | **One `BlogPost` aggregate** (`blog_posts`-backed) with `origin: carousel \| standalone`, linked to `EditorialProject`. `CarouselArticle` rejected. | A single blog representation removes the dual-model ambiguity. Embedded carousel blog columns migrate then drop (Phase 6); one `useBlogPosts()` hook survives. No second blog representation is kept. |
| 3 | Are Persona and Quality one bounded context or two? | **Two contexts** (`persona`, `quality`). | Deliberate deviation from the recommended single `persona_quality`. Persona owns `VoiceScore` and `PersonaAgent.enforce()`; quality consumes via persona's public contract (dependency: quality → persona). Separating them keeps voice ownership crisp and lets quality evolve its rubrics independently. |
| 4 | Should Editorial Operations be a module or only read projections? | **Full module now.** | Deliberate deviation from the recommended read-side-only default. It must own real behavior from day one (notification dispatch, board/calendar rules); its views remain event-built read models, never direct table joins into other contexts. |
| 5 | Which existing blog representation is authoritative? | **One `BlogPost` aggregate** backed by `blog_posts`; embedded carousel blog markdown/translations migrated then dropped; one `useBlogPosts()` survives. | The first-class `blog_posts` model is authoritative. The embedded carousel `blog_markdown` is a compatibility projection only until migrated. Resolves the two-`useBlogPosts()` collision (see appendix). |
| 6 | Operating context (users/traffic/checkpoints/tenancy)? | **Decided in ADR-0009 (AE-0072), not in this glossary.** | Recorded in the interview as "pre-production, single user, no external consumers → scaled-down + migrate-in-place track," but the authoritative architecture statement lives in ADR-0009 per the plan. |

---

## Naming-collision appendix

### Evidence: two `useBlogPosts()` hooks

Command run on 2026-06-12 from the repository root:

```console
$ rg -c "useBlogPosts" frontend/src
frontend/src/app/dashboard/blog-posts/[id]/edit/page.tsx:2
frontend/src/app/dashboard/blog-posts/page.tsx:2
frontend/src/features/blog/hooks/use-blog-posts.ts:1
frontend/src/features/blog/hooks/use-carousel-blog.ts:1
frontend/src/features/blog/hooks/use-carousel-blog.test.ts:3
frontend/src/features/blog/hooks/index.ts:1
```

Two different hooks are both named `useBlogPosts()`:

- `frontend/src/features/blog/hooks/use-carousel-blog.ts` — fetches completed
  **carousel projects** and renders them on the public `/blog` route.
- `frontend/src/features/blog/hooks/use-blog-posts.ts` — manages **first-class
  blog posts**.

The same identifier denoting two different concepts is the concrete symptom of
the overloaded blog model.

### Decision: the `CarouselArticle` split — one `BlogPost` survives

The collision is **why `CarouselArticle` was considered and then rejected**.
Rather than formalize the two meanings as two types (`CarouselArticle` +
`BlogPost`), the interview chose **one `BlogPost` aggregate** with
`origin: carousel | standalone`. Consequently:

- `CarouselArticle` is an **_Avoid_** term (rejected); use `BlogPost`
  (`origin = carousel`).
- Exactly **one `useBlogPosts()` hook survives** the migration (the
  first-class `blog_posts` one); the carousel-blog hook is folded into the
  single `BlogPost` model with `origin = carousel`.
- This is a target-language decision; the live duplicate hooks remain until
  the frontend alignment phase (Phase 7) per the compatibility note.
