# Phase 8 — Remove Legacy Layers and Adapters (epic plan)

**Planner output.** Source: `.agent/reports/domain-modularization.options.md` §"Phase 8: Remove legacy layers and
adapters" (lines 1061-1079) + the two consent-gated deferral records created during Phases 6/7: **AE-0133**
(backend — auto-publish cutover + destructive column drop) and **AE-0143** (frontend — shim removal, re-homing,
route thinning, identity module, schema-drift blocking). **Precondition: Phases 0-7 merged** (PRs #15-#21 — all
merged). This is the final roadmap phase: the modularization is functionally complete; Phase 8 removes the
temporary compatibility scaffolding (shims, re-exports, exact import-linter exceptions, grandfathered baselines)
and executes the two deliberately-deferred behavior/destructive changes — **with explicit owner consent and,
per the roadmap, after production observation.**

## Goal

Drive the temporary migration scaffolding to zero: delete the `@/features/*` and backend re-export shims, remove
global layer files whose ownership has fully moved into modules, shrink the exact Import-Linter `ignore_imports`
exceptions (currently 35) and the grandfathered import baselines as violations reach zero, retire stale
hand-maintained API-contract docs (now that OpenAPI is generated), and — consent-gated — execute the auto-publish
cutover (approval ≠ release) and the destructive drop of the embedded carousel blog/distribution columns.

## ⚠️ Scope decision (CRITICAL — read before validating)

Phase 8 has **two risk classes**; they must NOT be conflated:

**Class A — SAFE cleanup (behavior-preserving, no consent gate beyond normal review).** Removing dead
shims/re-exports/anchors, re-homing components, thinning route pages, shrinking import exceptions/baselines as
they reach zero, retiring stale docs. These are byte-identical / no-runtime-change and hold the existing green
gates (backend gates.sh 14/0/3 + check-integrity + arch-ratchet; frontend typecheck/lint/boundaries 0/url 26/
circular 0/822 tests/build/component-types ratchet). The boundary/exception ratchets only go DOWN.

**Class B — CONSENT-GATED (behavior change + destructive).** (1) the **auto-publish cutover** (approval and
public release become two distinct user actions — a real behavior change; the AE-0125 safety net is *updated to
the new behavior*) and (2) the **destructive Alembic migration** dropping `blog_markdown`/`blog_translations`/
`caption*`/`linkedin_post_*` from `carousel_projects` — **drain-gated** (every live LangGraph checkpoint finished
on pre-migration code or restarted with documented consent) and only after `blog_posts` is the confirmed single
writer. These STAY **Intake** until the owner explicitly schedules them (ADR-0008); they are reversible-by-backup
and must not run while a live checkpoint references the old shape.

**IN (this plan):** break Phase 8 into vertical slices (one ticket ≈ one branch), Class A as `Ready` (after
architect validation), Class B as `Intake` (consent-gated). Replace the two broad umbrella tickets AE-0133/0143
with focused slices that carry the real acceptance criteria; AE-0133/0143 become tracking records pointing here.

**DEFERRED / OUT:** splitting persistence tables for independent ownership — only "if it provides measurable
value" (roadmap); no evidence it does, so it is explicitly NOT in Phase 8.

## Reality vs. spec (2026-06-16 scan)

- **Frontend:** 12 `src/features/*` dirs remain as **re-export shims** (Phase 7 left them for compatibility);
  feature/module boundary baseline = **0**; component-type-location baseline = **57** (down-only ratchet, can
  shrink toward 0); a `modules/_example` anchor remains; the OpenAPI/Zod schema-drift check is **advisory** with
  **24 pre-existing drifts**; auth/session lives in `lib/` + `app/` (no `modules/identity` yet).
- **Backend:** `.importlinter` carries **35 `ignore_imports`** exact exceptions; import baselines grandfather
  `application→infra` (62), `api→infra` (76), `get_container` (14), `.commit()` sites — all down-only; legacy
  ACL/owner facades + some global `application/domain/infrastructure` files may now be dead post-extraction.
- **API docs:** `docs/architecture/API_CONTRACT.md` is hand-maintained; AE-0141 now generates
  `docs/architecture/openapi.json` from the app, making hand-kept sections stale/duplicative.
- **Deferred (Class B):** the auto-publish cutover (AE-0133) + the embedded-column drop (AE-0133) — both still
  pending; the approval≠release contract (AE-0111) + the additive `BlogPost.origin` backfill (AE-0127) are
  already in place as preconditions.

## Ticket breakdown

| ID | Title | Tier | Class | Area | Blocked by |
|----|-------|------|------|------|------------|
| **AE-0152** | Phase 8 epic: Remove legacy layers and adapters | T3 | — | Cross-cutting | — (tracks 0153-0171) |
| **AE-0153** | Frontend: remove `@/features/*` re-export shims + delete `src/features/` + drop `_example` anchor | T1 | A | Frontend | — |
| **AE-0154** | Frontend: exhaustive business-component re-homing; ratchet component-type-location baseline down (→0 target) | T2 | A | Frontend | AE-0153 |
| **AE-0155** | Frontend: route-page thinning (`app/**/page.tsx` → thin composition over module hooks) | T2 | A | Frontend | AE-0153 |
| **AE-0165** | Frontend: auth e2e safety net (login/logout/refresh/guard) — precondition for identity | T2 | A | Frontend/Tests | — |
| **AE-0156** | Frontend: `modules/identity` SLICE 1 — auth-specific client lib behind a contract (HTTP client stays in lib/) | T2 | A | Frontend | AE-0153, AE-0165 |
| **AE-0164** | Frontend: `modules/identity` SLICE 2 — relocate auth route handlers + guards behind the contract | T2 | A | Frontend | AE-0156 |
| **AE-0157** | Reconcile the 24 OpenAPI/Zod schema drifts to 0 + flip the schema-drift check to blocking | T2 | A | Frontend/CI | AE-0153 |
| **AE-0158** | Backend: remove dead compatibility re-exports/shims; ratchet import baselines (application/api→infra) down | T2 | A | Backend | — |
| **AE-0159** | Backend: shrink `.importlinter` exact `ignore_imports` exceptions as violations reach zero; delete dead global layer files | T2 | A | Backend/CI | AE-0158 |
| **AE-0160** | Retire stale hand-maintained API-contract doc sections (defer to generated OpenAPI from AE-0141) | T1 | A | Docs | AE-0158 |
| **AE-0163** | Backend: make `blog_posts` the single writer + remove embedded-column read fallback (de-risk the drop) | T2 | A | Backend | — |
| **AE-0161** | Backend: auto-publish cutover — approval ≠ release as two distinct user actions (BEHAVIOR CHANGE) | T2 | B | Backend/Frontend | — (consent) |
| **AE-0162** | Backend: drop embedded carousel blog/distribution columns (DESTRUCTIVE, drain-gated migration) | T2 | B | Backend/DB | AE-0163 (+consent+drain) |
| **AE-0166** | Harden ESLint: warnings→errors + use-client / useEffect / TanStack-Query-over-fetch rules | T2 | B | Frontend | — (kaizen) |
| **AE-0167** | CI build gate (`next build`) + group quality gates into frontend/backend categories (keep gates.sh) | T2 | B | Cross-cutting | — (kaizen) |
| **AE-0168** | Repair husky pre-commit + codify `--no-verify` policy (format/lint defense-in-depth) | T1 | B | Cross-cutting | — (kaizen) |
| **AE-0169** | Auto-scaffold dev-summary report on the Dev Complete transition | T1 | B | Cross-cutting | — (kaizen) |
| **AE-0170** | Worktree isolation + HEAD-detach guard for external QA/kaizen runs | T2 | B | Cross-cutting | — (kaizen) |
| **AE-0171** | check-integrity pre-flight: documented build-output dirs must be gitignored | T1 | B | Cross-cutting | — (kaizen) |

**Kaizen-originated Class-B follow-ups (AE-0166–0171):** emitted by the Phase 8 end-of-phase kaizen sweep
(`.agent/reports/kaizen-sweep-2026-06-16.*`, owner-approved). They are continuous-improvement *quality
enforcements* (all ratchet UP/HOLD) grouped into **Class B** at the owner's direction as deferred,
post-PR-#23 follow-up work — not behavior-change/destructive like AE-0161/0162, and they carry no
consent/drain gate (the Class-B grouping here means "deferred Phase-8 follow-up", scheduled separately).

> **CORRECTION 2026-06-17 (architect research + cold-critic skeptical review).**
> The claim below that "AE-0163 makes `blog_posts` the **sole writer**" of the
> embedded columns is **inaccurate**. AE-0163's implementation
> (`carousel_blog_dual_write.py`) only consolidated the blog **body**
> (`blog_markdown`/`blog_translations`) into `blog_posts.content`. The four
> distribution columns (`caption`, `caption_en`, `linkedin_post_pt`,
> `linkedin_post_en`) were **never given a canonical home or backfill** and remain
> the sole source, still read AND written. The destructive drop is therefore SPLIT:
> **AE-0162** = blog columns only (Low priority; gated on retiring the remaining
> blog writers incl. the dual-write's self-read of `blog_markdown`); **AE-0204** =
> add a `blog_posts.distribution` JSONB home for caption/LinkedIn (the real
> blocker); **AE-0205** = drop the distribution columns (blocked by AE-0204);
> **AE-0206** = delete the write-dead `caption_en`. See those tickets for the
> validated plan.

(AE-0133 → superseded by AE-0161 + AE-0162; AE-0143 → superseded by AE-0153-0157.
**Round-1 architect fixes:** AE-0163 added as the behavior-preserving de-risking PREDECESSOR to the destructive
drop — the embedded columns are still LIVE READS (per-field fallback + the `blog_markdown` 404 gate) with 4+
writers, so AE-0162 can't drop them until AE-0163 makes `blog_posts` the sole writer and removes the read
fallback. AE-0156 (identity) split into SLICE 1 (auth client lib — the shared `authenticated-fetch`/`server-fetch`
HTTP client STAYS in `lib/`) + AE-0164 (route handlers/guards), gated on the new AE-0165 auth e2e. AE-0157's
spurious `→AE-0156` dependency removed.)

## Risks & guardrails

- **Class A is behavior-preserving.** Each cleanup ticket holds the green gates + ratchets down-only; deletions
  are gated on "no remaining importer" (grep/typecheck/lint:boundaries proof) — never delete a path with a live
  consumer. Re-export-shim removal must follow a clean importer-zero check.
- **Class B is consent-gated + reversible.** AE-0161 updates the safety net to the NEW approval≠release behavior
  (it is the one place behavior changes). AE-0162 (the destructive drop) is reversible-by-backup, drain-gated, and
  blocked by **AE-0163** — a behavior-preserving Class-A predecessor that makes `blog_posts` the SOLE writer AND
  removes the embedded-column READ fallback (today `resolve_blog_body` + the `blog_markdown` 404 gate still read
  the columns, and 4+ writers remain — so they cannot be dropped until AE-0163 lands). Neither AE-0161 nor AE-0162
  starts without explicit owner consent (Status: Intake), after production observation of Phases 0-7.
- **Identity is route-adjacent** and was split (architect round 1): AE-0156 moves only the auth-SPECIFIC client
  lib (the shared `authenticated-fetch`/`server-fetch` HTTP client STAYS in `lib/`), AE-0164 relocates the route
  handlers/guards — both gated on the **AE-0165** auth e2e (login/logout/refresh/guard) added so byte-identical
  auth behavior is actually provable.
- **Exit-gate enforcement.** Removing an `ignore_imports` exception or ratcheting a baseline must keep
  `lint-imports` / `import_baseline.py --check` / `lint:boundaries` green at the new lower number.
- **No "big-bang."** Vertical slices, merged independently; the destructive drop (AE-0162) goes last, alone.

## Epic exit gate (roadmap Phase 8)

- No production import uses legacy module paths (`src/features/*` deleted; backend re-export shims gone).
- Architecture rules pass **without broad ignores**: `.importlinter` exact exceptions shrunk to the minimum
  (AE-0126 object-identity shims only, or zero); import baselines at their true floor; frontend boundary 0 +
  component-type-location ratcheted toward 0; schema-drift check blocking at drift 0.
- Migration + rollback proven for the destructive drop (Class B), executed only with consent + checkpoint-drain.
- Stale hand-maintained API-contract sections retired in favor of generated OpenAPI.

## Suggested order (waves)

- **Wave A (frontend cleanup, SERIALIZED on the `app/`-touching slices):** AE-0153 first (unblocks the rest);
  AE-0157 (schema-drift → blocking) can run anytime after AE-0153 (independent of identity). The `app/`-touching
  slices serialize to avoid the Phase-7 collision: AE-0165 (auth e2e) → AE-0156 (identity slice 1) → AE-0164
  (identity slice 2) → then AE-0154 ∥ AE-0155 (re-homing / route thinning).
- **Wave B (backend cleanup, alongside Wave A — disjoint trees):** AE-0158 → AE-0159 → AE-0160; AE-0163
  (writer-consolidation, behavior-preserving) runs here too (de-risks the Class-B drop).
- **Wave C (consent-gated, LAST, only on explicit go-ahead, after production observation):** AE-0161 (cutover —
  independent) and AE-0162 (destructive drop — blocked by AE-0163, drain-gated, alone).

## Handoff

→ `/architect-skill` validate loop (confirm AE-0152-0165 Ready/Intake split is right; SCRUTINIZE: is the
Class-A/Class-B risk partition correct; are the deletion-safety preconditions sufficient; does AE-0156 identity
belong in Phase 8 or is it its own mini-phase; is AE-0162's drain-gate spec complete?), then execute Wave A/B
(Class A) with the developer + QA loop; hold Wave C (Class B) for explicit owner consent.
