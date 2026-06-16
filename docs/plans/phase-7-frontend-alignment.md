# Phase 7 — Align the Frontend to Bounded Contexts (epic plan)

**Planner output.** Source: `.agent/reports/domain-modularization.options.md` §"Phase 7: Align the frontend"
(lines 1040-1059), the Target Frontend Tree (lines 554-606), the Module Contract Rules (lines 608+), and the
round-2 corrections (frontend baseline does not reproduce → re-measure first; two `useBlogPosts()` hooks →
the `CarouselArticle` vs `BlogPost` split is mandatory). Builds on merged backend Phases 0-6 (the accepted
context glossary: `knowledge, identity, conversation, editorial, presentation, publishing`). **Precondition:
Phase 6 (PR #20) merged** (glossary final). Reuses the existing frontend feature-boundary ratchet
(`scripts/check-feature-boundaries.mjs`, baseline 23) as the down-only enforcement mechanism — the analog of
the backend AE-0082 import baseline.

## Goal

Reorganize `frontend/src/features/**` into bounded-context **modules** that share the backend glossary, behind
**public contracts** (a `public`/`index.ts` barrel per module; feature internals cannot cross-import without
it). Co-locate API/Zod/query contracts per module, move business-specific components out of the global atomic
folders into their owning module, add OpenAPI/Zod **schema-drift checking**, and **ratchet the cross-context
edge count DOWN** from 23. **App Router URLs stay unchanged**; route pages become thin composition components.

## ⚠️ Scope decision (CRITICAL — read before validating)

Phase 7 is a **behavior-preserving** frontend reorganization, NOT a redesign. The discipline mirrors the
backend phases: green gates stay green, no observable UI/behavior change, no route URL changes, the
boundary-edge ratchet only goes DOWN. Because the frontend has no byte-identical HTTP safety net, the safety
net IS: `typecheck` (tsc strict, clean) + `lint` (eslint, clean) + `lint:boundaries` (ratchet) + `test`
(Vitest, 822 passing) + `check:legacy` + the App-Router URL inventory — all held green per ticket.

**IN (behavior-preserving + incremental):**
- Documented frontend **baseline** (file/LOC methodology + the green-gate snapshot) — closes the round-2
  "baseline does not reproduce" finding before any move.
- Introduce `frontend/src/modules/<context>/` with a **public contract** convention (barrel + a module-boundary
  lint rule extending the existing feature-boundary ratchet); migrate features → modules **by bounded context**,
  each behind its contract, keeping `@/` import paths resolvable (re-export shims where a path must keep working,
  mirroring the backend object-identity shims).
- Disambiguate the two `useBlogPosts()` hooks: `use-carousel-blog.ts` (carousel-derived **CarouselArticle**)
  vs `use-blog-posts.ts` (first-class **BlogPost**) — align names to the backend `BlogPost.origin` split.
- Co-locate API/Zod/query contracts per module; move clearly-owned business components (`BlogPostCard`,
  `PersonaCard`, the workflow board) out of `components/atoms|molecules|organisms` into their module.
- Add an **OpenAPI/Zod schema-drift check** (frontend Zod schemas vs the backend OpenAPI) as an advisory→blocking CI gate.
- Ratchet `check-feature-boundaries` DOWN as contracts replace cross-feature imports.

**DEFERRED (explicitly out of Phase 7 — documented follow-up):**
- Exhaustive re-homing of every shared component (do the clearly-owned ones; generic `Neon*` stays atomic).
- Any change requiring backend edits (Phase 7 is frontend-only).
- The full `app/` route-page thinning beyond extracting data/composition into module hooks (cosmetic page
  splits that risk behavior are deferred).
- Deleting legacy compatibility shims (Phase 8 cleanup).

## Reality vs. spec (2026-06-16 frontend scan)

- **Baseline green:** `typecheck` clean, `eslint --quiet` clean, `lint:boundaries` OK (23 grandfathered edges,
  ceiling 23, 0 new), `test` 75 files / **822 passing**. (The roadmap's "406 TS files / 41,638 lines" does not
  reproduce; actual ≈305 non-test files / ≈25.7k lines — AE-0135 documents the real methodology.)
- **12 features** (non-test LOC): create 2088, blog 2065, publish 1142, dashboard 938, knowledge 934,
  workflow 752, chat 426, rubrics 146, persona 144, carousel 133, personas 91, analytics 50.
- **Existing enforcement:** `scripts/check-feature-boundaries.mjs` + `scripts/feature-boundary-baseline.json`
  (23 edges, format `src/features/X/file::Y`); `npm run check:legacy` (v1 removal guard). NO module layer yet.
- **Persona/personas duplication** (144 + 91 LOC) → consolidate under `persona-quality`.
- **Two `useBlogPosts()`** under `features/blog/hooks/` (carousel-article vs blog-post).

## Target context mapping (feature → module)

| Current feature(s) | Target module |
|---|---|
| blog, publish | **publishing** (blog / distribution / scheduling) |
| carousel | **carousel-presentation** (preview / review / refinement) |
| create, workflow | **editorial** (workspace / workflow / sources) |
| dashboard, analytics | **editorial-operations** (board / analytics) |
| persona, personas, rubrics | **persona-quality** |
| chat | **conversation** |
| knowledge | **knowledge** |
| (auth/session) | **identity** |

## Ticket breakdown

| ID | Title | Tier | Area | Blocked by |
|----|-------|------|------|------------|
| **AE-0134** | Phase 7 epic: Align the frontend to bounded contexts | T3 | Cross-cutting | — (tracks 0135-0142) |
| **AE-0135** | Documented frontend baseline (file/LOC methodology + green-gate snapshot) + context-mapping doc | T2 | Frontend/Docs | — |
| **AE-0136** | `modules/` scaffolding + public-contract convention + module-boundary lint rule (extends the feature-boundary ratchet) | T2 | Frontend/CI | AE-0135 |
| **AE-0137** | Disambiguate `useBlogPosts` (CarouselArticle vs BlogPost) + publishing module (blog/distribution/scheduling) behind a public contract | T2 | Frontend | AE-0136 |
| **AE-0138** | editorial + editorial-operations modules (create/workflow → editorial; dashboard/analytics → editorial-operations) behind contracts | T2 | Frontend | AE-0136 |
| **AE-0139** | carousel-presentation + persona-quality + conversation + knowledge + identity modules behind contracts | T2 | Frontend | AE-0136 |
| **AE-0140** | Co-locate API/Zod/query contracts per module; move business components out of global atomic folders | T2 | Frontend | AE-0137, AE-0138, AE-0139 |
| **AE-0141** | OpenAPI/Zod schema-drift check (frontend ↔ backend) — advisory→blocking | T2 | Frontend/CI | AE-0140 |
| **AE-0142** | Frontend module-boundary exit gate + ratchet down + glossary/convention docs + deferred follow-up (Phase 8) | T2 | Frontend/CI | AE-0137, AE-0138, AE-0139, AE-0140, AE-0141 |

## Suggested order (waves)

- **Wave A:** AE-0135 (baseline+map), AE-0136 (scaffolding + boundary rule).
- **Wave B (parallel by context):** AE-0137 (publishing), AE-0138 (editorial/-operations), AE-0139 (the rest).
- **Wave C:** AE-0140 (contract co-location + component re-homing — needs the modules).
- **Wave D:** AE-0141 (schema-drift check).
- **Wave E:** AE-0142 (exit gate + ratchet + docs).

## Risks & guardrails

- **Behavior-preserving.** Keep all App Router URLs; route pages keep rendering the same components/data. The
  822 Vitest tests + typecheck + eslint + `check:legacy` stay green per ticket; no snapshot/test deleted.
- **Down-only ratchet.** `check-feature-boundaries` ceiling never rises; each context migration replaces
  cross-feature imports with public-contract imports and ratchets the count DOWN (or holds).
- **Re-export shims** keep `@/features/...` and `@/components/...` paths resolving during migration (object-
  identity, mirroring the backend AE-0126 shims) so no consumer breaks mid-phase.
- **No backend changes.** Frontend-only; the schema-drift check is read-only against the backend OpenAPI.
- **ZERO gate-gaming.** No new eslint-disable / `@ts-ignore` / `@ts-expect-error` / skipped tests / lowered
  thresholds / boundary-baseline additions (the baseline only shrinks).

## Epic exit gate (Phase-7 IN scope)

- Features reorganized under `modules/<context>` sharing the backend glossary; feature internals reachable only
  via each module's public contract (enforced by the module-boundary lint rule).
- Route pages are thin composition components; App Router URLs unchanged.
- The two blog hooks disambiguated (CarouselArticle vs BlogPost); persona/personas consolidated.
- API/Zod/query contracts co-located per module; business components out of the global atomic folders.
- OpenAPI/Zod schema-drift check in CI.
- `typecheck` + `lint` + `lint:boundaries` (ratcheted down) + `test` (822+) + `check:legacy` green.

## Handoff

→ `/architect-skill` validate loop (confirm AE-0134-0142 Ready; SCRUTINIZE the scope decision — is the
behavior-preserving, ratchet-down, URLs-unchanged subset right, and is the safety net (typecheck+lint+
boundaries+test) sufficient without a byte-identical HTTP net?), then execute Waves A→E with the
developer + QA loop.
