# Phase 7 — Frontend Baseline & Context Map (AE-0135)

Documented baseline for the Phase 7 frontend bounded-context alignment. Closes the round-2
"frontend baseline does not reproduce" finding by recording a **reproducible measurement methodology** and the
**green-gate snapshot** that subsequent Phase 7 tickets must preserve. Behavior-preserving discipline: every
later Phase 7 ticket holds these gates green and ratchets the boundary count down-only.

## Measurement methodology (reproducible)

Non-test production source = files under `frontend/src` matching `*.ts`/`*.tsx`, EXCLUDING `*.test.ts`,
`*.test.tsx`, and `*.stories.tsx`:

```bash
cd frontend
# file count
find src -type f \( -name "*.ts" -o -name "*.tsx" \) \
  ! -name "*.test.ts" ! -name "*.test.tsx" ! -name "*.stories.tsx" | wc -l
# LOC
find src -type f \( -name "*.ts" -o -name "*.tsx" \) \
  ! -name "*.test.ts" ! -name "*.test.tsx" ! -name "*.stories.tsx" -exec cat {} + | wc -l
```

## Baseline measurement (2026-06-16)

- **Non-test production files:** 306
- **Non-test production LOC:** 25,793

> Measured pre-AE-0136. AE-0136 added the `modules/_example` public-API anchor (`src/modules/_example/index.ts`),
> a single non-feature scaffolding file (+1 file / +16 LOC → 307 files / 25,809 LOC post-scaffolding).

| `src/` area | non-test LOC |
|---|---:|
| app | 10,409 |
| features | 8,909 |
| components | 3,613 |
| lib | 1,007 |
| constants | 883 |
| schemas | 513 |
| hooks | 67 |
| i18n | 21 |

Per-feature non-test LOC:

| feature | LOC | feature | LOC |
|---|---:|---|---:|
| create | 2,088 | chat | 426 |
| blog | 2,065 | rubrics | 146 |
| publish | 1,142 | persona | 144 |
| dashboard | 938 | carousel | 133 |
| knowledge | 934 | personas | 91 |
| workflow | 752 | analytics | 50 |

> The roadmap's "406 TS/TSX files / 41,638 lines" (and 15,036 across five features) does **not** reproduce; the
> accurate figures are ~306 non-test files / ~25.8k lines, features summing to ~8.9k. This doc is the
> authoritative baseline; the overall Phase-7 estimate is re-confirmed against it.

## Green-gate snapshot (the Phase 7 safety net)

All green at baseline (2026-06-16); every Phase 7 ticket must keep them green:

| Gate | Command | Baseline result |
|---|---|---|
| Types | `npm run typecheck` | clean (tsc --noEmit, strict) |
| Lint | `npm run lint` (eslint --quiet) | clean |
| Boundaries | `npm run lint:boundaries` | OK — 23 grandfathered cross-feature edges, ceiling 23, 0 new |
| Unit tests | `npm run test` (Vitest) | 75 files, **822 passing** |
| Legacy guard | `npm run check:legacy` | pass (no v1 imports) |

Phase 7 ADDS (AE-0136): an App-Router URL-inventory check (`npm run url:check`) and a **dependency-free**
circular-import check (`npm run lint:circular`, Tarjan SCC — not madge), both chained into `npm run lint` so
they gate; plus `npm run build` run as a per-migration-ticket gate (not chained into `lint` because it is slow).
These cover what tsc/eslint/Vitest miss: RSC/`'use client'` boundaries, route segment config (`export const
dynamic` in the public `/blog` pages), `next/dynamic`, and barrel-induced circular imports.

## Feature → module context map (accepted glossary)

Alignment is to `docs/architecture/domain-glossary.md` (the accepted 9-context map). `persona` and `quality`
are TWO contexts (`quality` → `persona`, one-way, via persona's public contract); `persona_quality` is
forbidden. `CarouselArticle` is a rejected term — the canonical concept is `BlogPost (origin = carousel)`.

| Current feature(s) | Target module | Notes |
|---|---|---|
| blog, publish | **publishing** (blog / distribution / scheduling) | disambiguate the two `useBlogPosts` hooks: `useCarouselBlogPosts` (origin=carousel) vs `useBlogPosts` (first-class) |
| carousel | **carousel-presentation** (preview / review / refinement) | |
| create, workflow | **editorial** (workspace / workflow / sources) | |
| dashboard, analytics | **editorial-operations** (board / analytics) | |
| persona, personas | **persona** | consolidate the persona/personas duplication |
| rubrics | **quality** | owns quality rubrics; depends on `persona` via its public contract |
| chat | **conversation** | |
| knowledge | **knowledge** | |
| (auth/session) | **identity** | no `features/auth`; auth/session stays in `lib/` + `app/` — frontend identity consolidation **deferred to Phase 8** |

## OpenAPI ↔ Zod schema-drift check (AE-0141)

Phase 7 adds a schema-drift check that compares the frontend domain Zod schemas against the **actual** backend
OpenAPI contract, so divergence between what the API returns and what the UI validates surfaces in CI instead of
at runtime.

**Two parts:**

1. **Read-only OpenAPI exporter** — `backend/scripts/export_openapi.py` builds the app via the canonical
   `create_app()` and writes `app.openapi()` to the committed artifact `docs/architecture/openapi.json`
   (stable, `sort_keys` JSON). It is a generator, not a behavior change: it only reads the schema FastAPI already
   builds and alters no route/schema/response. It runs with **no live keys** — `create_app()` uses lazy external
   clients (Pinecone/OpenAI build on first use, not at construction), so `app.openapi()` (which walks routes +
   Pydantic models only) needs no network/DB/secrets. The same keyless `create_app()` path is exercised by
   `backend/tests/unit/test_route_snapshot.py`.

   ```bash
   uv run python backend/scripts/export_openapi.py            # regenerate the artifact
   uv run python backend/scripts/export_openapi.py --check    # fail if the artifact is stale
   ```

2. **Frontend drift checker** — `frontend/scripts/check-schema-drift.mjs` (npm `check:schema-drift`) loads the
   artifact, parses a **curated mapping** of frontend Zod schemas (`src/schemas/{chat,knowledge,carousel}.ts`)
   to their OpenAPI component counterparts, and reports drift.

**What's compared** (per mapped schema): field presence (frontend-extra fields the API no longer declares;
API fields — required vs optional — the frontend omits), coarse type (`string`/`number`/`boolean`/`array`/
`object`), and nullability/optionality (handling the Pydantic `anyOf [T, null]` encoding). `z.unknown()`,
nested-schema refs, and `.refine()`-wrapped composites are treated as opaque (no false type assertions). The
mapping deliberately excludes design-system `neon-*` prop schemas (not API DTOs).

**Advisory → blocking path.** The checker is **advisory-first**: it prints a report and exits 0 even when drift
exists, so it can be wired into CI without gating on pre-existing drift. It is registered as the
`schema-drift` frontend gate in `scripts/ci/gates.sh` and runs in the **non-blocking**
`frontend / Schema drift (advisory)` job (`continue-on-error: true`), mirroring the mutation-advisory pattern.
Pass `--strict` to make it exit 1 on drift; flip CI to that once the report reaches 0.

**Drift recorded at introduction (2026-06-16, advisory baseline).** 24 findings across the mapped schemas — all
**pre-existing**, none introduced by this ticket:

| Mapped schema | Drift |
|---|---|
| `messageSchema` → `MessageResponse` | `sources` nullable in API, required in Zod |
| `chatResponseSchema` → `ChatResponse` | `sources` nullable in API, required in Zod |
| `documentSchema` → `DocumentResponse` | missing API fields `is_public`, `scope` |
| `createDocumentRequestSchema` → `DocumentCreate` | unmodeled optional `is_public`, `scope` |
| `documentUploadResponseSchema` → `DocumentUploadResponse` | missing API fields `is_public`, `scope` |
| `carouselProjectResponseSchema` → `CarouselProjectResponse` | missing required `accent_color`, `background_color`, `primary_color`; unmodeled `current_phase`, `error_message`, `image_model`, `image_style`, `is_public`, `output_dir`, `phase_status`, `research_sources`, `slides` |
| `carouselSlideResponseSchema` → `CarouselSlideResponse` | frontend-extra `project_id`, `image_prompt`; unmodeled API `image_path`; missing required `updated_at` |

Reconciling this drift (and then flipping the gate to `--strict`) is follow-up work — `AE-0141` only delivers the
mechanism + the advisory baseline.

## Migration discipline

- App Router URLs unchanged; route pages stay thin composition components.
- Each module exposes a public contract (`modules/<context>/index.ts`); internals are reachable only through it
  (enforced by the AE-0136 boundary-checker refactor, which also covers the `app/` consumer layer).
- Re-export shims keep `@/features/...` / `@/components/...` paths resolving during migration (object-identity,
  mirroring the backend AE-0126 shims).
- The boundary ratchet only goes DOWN; no eslint-disable / `@ts-ignore` / `@ts-expect-error` / skipped tests /
  lowered thresholds / baseline additions.
