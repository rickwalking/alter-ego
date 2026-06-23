---
status: proposed
date: 2026-06-23
decision-makers: Pedro Marins
consulted: architect-skill
informed: delivery team
---

# ADR-0019: Palettes as a hybrid catalog (typed root registry + DB-backed custom palettes)

## Context and Problem Statement

AE-0266 made carousel palettes a closed, typed code registry (`PALETTE_REGISTRY`)
— the single source of truth, emitted to `docs/contracts/palettes.json` and
guarded by a frontend drift gate. The product now needs a **catalog the frontend
can add to and edit**: users create new palettes at runtime, shown alongside the
curated originals, shared globally.

This requires palettes to be **runtime data** (mutable rows) — the opposite of the
compile-time code registry just shipped. How do we add user-creatable palettes
without losing the invariants (light-not-AUTO, light→light image style, brand
color-lock) that the typed registry guarantees, and without a risky big-bang
rewrite of the carousel theme model?

## Decision Drivers

- Preserve AE-0266's structural guarantees for the curated/brand-locked palettes.
- Make the AE-0264 light-on-dark rendering bug impossible for user palettes too.
- Keep `resolve_theme` behavior (brand precedence, AUTO rotation) intact.
- Contain the prod-DB migration risk (history of Alembic drift in prod).
- Treat user-supplied colors as an LLM prompt-injection surface.

## Considered Options

1. **All palettes in the DB** — migrate roots + custom to one table; registry deleted.
2. **All palettes in a hand-edited JSON** — roots + custom in JSON, loaded + validated.
3. **Hybrid (chosen)** — roots stay a typed code registry emitted to JSON
   (read-only); custom palettes are global DB rows; one resolver over the union.

## Decision Outcome

Chosen: **Option 3 (hybrid)**.

- **Root palettes** remain authored in `PALETTE_REGISTRY` and emitted to
  `palettes.json`; served read-only. Compile-time invariants retained.
- **Custom palettes** are rows in a global `palettes` table (no per-user scope),
  created/edited/soft-deleted via a CRUD API. `image_style` is **derived from
  `mode`** (not stored, not user-picked), so it can never contradict the palette —
  this is what makes the AE-0264 class structurally impossible for custom palettes.
- **`project.theme` becomes a string reference** — a root key, the `"auto"`
  sentinel, or a custom palette's **immutable UUID `id`** (never its slug) —
  replacing the `CarouselTheme` enum as the project field/column type. The enum is
  retained only as the canonical root-key list. The DB column converts **in place**
  (`USING theme::text`, expand-only — existing enum values are already valid
  strings); recovery is **roll-forward**, not `alembic downgrade`, given prod's
  history of Alembic drift.
- **`resolve_theme` becomes an application service** with a `PaletteRepository`
  port: it resolves root keys from the registry and custom ids/keywords from the
  DB, merged. This crosses the previously-pure resolver's I/O boundary — an
  accepted, explicit consequence.
- **Carousels snapshot their resolved palette at generation** (`theme_snapshot`
  JSONB on `carousel_projects`); they render from the snapshot, so palette edits or
  archival never alter already-generated carousels (edits do **not** propagate).
  `theme` records the user's choice; the snapshot records the resolved result.
- Archived (soft-deleted) palettes leave the catalog for new carousels; existing
  carousels are unaffected because they render from their snapshot.

### Consequences

- **Good:** user-creatable catalog without losing root guarantees; the AE-0264
  light-on-dark bug is unrepresentable for custom palettes; phased rollout keeps
  the prod migration isolated and reversible.
- **Good:** the Phase-2 `IMAGE_STRATEGY_REGISTRY` consolidation pays off — deriving
  style from mode is a single lookup.
- **Bad / cost:** `theme` enum→string migration touches a prod DB column and ~9
  source files; `resolve_theme` loses its purity (now needs a repository).
- **Bad / cost:** the AE-0266 Phase-3 frontend drift gate **partially dissolves** —
  once the FE renders the catalog dynamically, the hardcoded theme lists it guards
  disappear, so the gate is retargeted to the still-static surface (image presets,
  root keys). This ADR explicitly supersedes the optional AE-0266 Phase 4.
- **Security:** user-supplied colors flow into the LLM image prompt → strict
  server-side `#rrggbb` validation is mandatory; keywords are sanitized. Catalog
  writes are authenticated but **not owner-restricted** (any authed user may
  edit/archive any custom palette — product owner call for a small trusted team);
  `created_by` + soft-delete provide audit and no-hard-loss safety nets.

## More Information

Architecture plan: `.agent/reports/AE-0267.arch-plan.md` (modules, data model, API,
phased rollout P1–P4, open questions). Supersedes the "Phase 4" bullet of AE-0266.
Builds on ADR-0018 (declarative palette registry). Frontend visual/UX design of the
catalog is delegated to the `impeccable` skill as a parallel track.

Reviewed by **two** external cold critics (blind packets, separate sessions):
- `gemini-2.5-pro` — `.agent/reports/AE-0267.skeptical-review.md`. PROCEED_WITH_CAUTION;
  3 WARN (slug-as-FK, migration/rollback, concurrency races) → resolved (id-as-FK +
  immutable unique slug; expand-only migration + staging trial + roll-forward;
  DB-level partial-unique/`409`).
- `glm-5.2` via OpenCode — `.agent/reports/AE-0267.skeptical-review-glm.md`. WARN;
  went deeper. Its root finding (palette edits propagating → silent recolor, AUTO
  drift, cost/abuse) drove the **snapshot-at-generation** decision above. Other
  findings resolved: resolver cache+fallback, a pre-P1 prod value census gate,
  co-deploy/feature-flag P3+P4, keyword-overlap guards + rate-limits, slug/name
  charset+XSS spec. Phase-2 (`IMAGE_STRATEGY_REGISTRY`) dependency confirmed shipped.
