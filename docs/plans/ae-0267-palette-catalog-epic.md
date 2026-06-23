# AE-0267 — Epic: user-creatable global palette catalog

Planner: planner-skill · Date: 2026-06-23 · Tier: T3 (epic)
Architecture: `.agent/reports/AE-0267.arch-plan.md` · ADR: `docs/decisions/0019-palettes-as-data.md`
Skeptical reviews: `.agent/reports/AE-0267.skeptical-review.md` (gemini-2.5-pro),
`.agent/reports/AE-0267.skeptical-review-glm.md` (glm-5.2). Supersedes AE-0266 Phase 4.

## Goal

A **catalog** where curated *root* palettes (typed registry → `palettes.json`,
read-only) coexist with *custom* palettes that any authed user creates/edits from the
frontend. Custom palettes are global, soft-deletable; image style is **derived from
light/dark mode**; carousels **snapshot their resolved palette at generation** so edits
never alter past work.

## Resolved decisions (constraints for every child ticket)

| # | Decision |
|---|----------|
| D1 | Hybrid SoT: roots = typed registry emitted to JSON (read-only); custom = DB. |
| D2 | Catalog is global (no per-user scope; `created_by` for audit). |
| D3 | Image style **derived from mode** (light→`flat_editorial`, dark→default); never user-picked. |
| D4 | Soft-delete (archived flag); existing carousels unaffected (render from snapshot). |
| D5 | Custom palettes carry keywords (AUTO detection); guarded (see G5). |
| D6 | `project.theme` = string reference (root key \| `"auto"` \| custom **UUID id**, never slug). |
| D7 | Any authed user can add/edit/archive (no owner-restriction). |
| D8 | `slug` display-only, immutable, globally unique incl. archived; never the FK. |
| D9 | **Snapshot at generation** (`carousel_projects.theme_snapshot` JSONB); edits don't propagate. |
| O3 | Custom palettes get a **single user-typed name** (recommend); roots keep en/pt i18n. |

## Ticket breakdown

| ID | Title | Tier | Area | Depends on |
|----|-------|------|------|------------|
| AE-0267 | (epic) user-creatable global palette catalog | T3 | epic | — |
| AE-0268 | P1: `project.theme` enum→string reference (+ prod census gate) | T2 | backend, DB | — |
| AE-0269 | P2: custom-palette persistence + DB-backed resolver + snapshot | T2 | backend, DB | AE-0268 |
| AE-0270 | P3: palette CRUD API + security/validation | T2 | backend, API | AE-0269 |
| AE-0271 | P4: frontend dynamic catalog + create/edit + gate retarget | T2 | frontend | AE-0269 (co-ship with AE-0270) |

Vertical-slice note: AE-0270 (backend CRUD) ships **behind a feature flag** and
AE-0271 (FE) flips it; the two **must reach prod together** (skeptical G6 — no window
where customs are writable but invisible/unguarded).

---

### AE-0268 — P1: `project.theme` enum → string reference (+ prod census gate)

**Scope:** Replace `CarouselTheme` enum as the type of `CarouselProject.theme` (domain
+ DB column) with a `str` reference. Retain the enum only as the canonical root-key
list. No new behavior — resolver still reads only the registry.

**Acceptance criteria:**
- [ ] **Pre-migration gate (blocking):** capture prod `pg_typeof(carousel_projects.theme)`,
      actual column DDL/CHECK, and `SELECT theme, count(*) … GROUP BY 1`; assert every
      value is a current root key or `"auto"`. Attach output to the ticket. (G4)
- [ ] Migration is **expand-only / in-place** (`USING theme::text`, zero row rewrite);
      existing values round-trip; CHECK (if any) widened, not dropped silently.
- [ ] Recovery is **roll-forward** (a follow-up migration), NOT `alembic downgrade`;
      a tested downgrade-failure contingency is documented. (G2/F2)
- [ ] Post-deploy **monitoring query** confirms all `theme` values resolvable + row
      counts unchanged.
- [ ] All ~9 `CarouselTheme` references updated; `theme.value` reads become direct;
      mypy strict + full gates green; no public/user-visible behavior change asserted.
- [ ] Migration trialed (upgrade + downgrade) on a **staging DB restored from a current,
      unsanitized prod backup**. (G4)

**Risks:** prod DB drift (known) — the census gate is the mitigation. **Ships alone first.**
**`.feature`:** pure refactor + CI/migration → unit tests + migration round-trip test
suffice (document the no-behavior-change assertion).

---

### AE-0269 — P2: custom-palette persistence + DB-backed resolver + snapshot

**Scope:** New `palettes` table + `PaletteRepository` (port + async SQLAlchemy adapter).
`resolve_theme` becomes an application service over the union (registry roots + DB
custom). Add `carousel_projects.theme_snapshot` and freeze the resolved palette at
generation. No FE; API read-only (`GET` may include custom, none exist yet).

**Acceptance criteria:**
- [ ] `palettes` table per data model: uuid id (PK), name, slug, primary/accent/background,
      mode, keywords JSONB, archived, audit cols.
- [ ] DB constraints: **partial unique index `(name) WHERE archived=false`**; unique `slug`
      (all rows). (G3/F3)
- [ ] Resolver resolves root key / custom UUID id (active OR archived) / `"auto"`; brand
      precedence preserved; AUTO over (root brand ∪ custom keywords) for matching, root
      AUTO pool for hash fallback.
- [ ] **Image style derived from mode** via `IMAGE_STRATEGY_REGISTRY` (Phase-2, shipped);
      a light palette can never resolve to a dark strategy (regression test). (D3)
- [ ] **Snapshot (D9):** generation writes `theme_snapshot`; render/regeneration read the
      snapshot and never re-resolve; `theme="auto"` frozen at first generation.
- [ ] **Reliability (G2):** in-process LRU+TTL cache (invalidated on write); **registry-only
      fallback** when the repo is unavailable (logged + metric, no 500); resolver-latency metric.
- [ ] Migration additive (`theme_snapshot`), reversible.

**Risks:** resolver reliability regression (mitigated by cache + fallback), purity-boundary
shift (documented in ADR). **`.feature` required** (behavior-changing): resolver paths,
snapshot stability, degraded mode.

---

### AE-0270 — P3: palette CRUD API + security/validation (feature-flagged)

**Scope:** `POST/GET/PATCH/DELETE` palette endpoints behind a feature flag. Pydantic
validation + security. Roots are read-only (PATCH/DELETE → 403/404).

**Acceptance criteria:**
- [ ] `GET` returns roots ∪ active custom (the catalog/create-form source).
- [ ] `POST` creates custom: **strict `#rrggbb` hex** on all three colors (reject otherwise —
      prompt-injection surface, G5); mode required; image_style NOT accepted (derived).
- [ ] `PATCH` edits custom only; **rejects slug changes** (D8); roots forbidden.
- [ ] `DELETE` = soft-delete (sets archived).
- [ ] **Keyword guards (G5):** reject overlap with root brand keywords; cap count +
      per-keyword length; dedupe across active catalog; sanitize.
- [ ] **slug** generated URL-safe (reject `/`, `..`, reserved routes), immutable; **name**
      length-capped + escaped-on-render (XSS). (G8)
- [ ] Concurrent same-name `POST` → exactly one wins, other `409` (maps IntegrityError). (F3)
- [ ] AuthN required; no owner restriction (D7); **rate-limit POST and PATCH/DELETE**.
- [ ] Endpoints behind a flag OFF in prod until AE-0271 ships (G6).

**Risks:** prompt-injection via colors, AUTO-capture via keywords, abuse — all addressed by
validation/guards/rate-limits above. **`.feature` required.** Security review mandatory.

---

### AE-0271 — P4: frontend dynamic catalog + create/edit + gate retarget

**Scope:** Catalog view + create/edit form consuming `GET /palettes` dynamically (replace
hardcoded `CAROUSEL_THEMES`/`THEME_LABEL_KEYS`/`LIGHT_THEME_KEYS`). Flip the AE-0270 flag.
**Visual/UX design delegated to the `impeccable` skill.**

**Acceptance criteria:**
- [ ] Create-page theme dropdown renders roots ∪ active custom from the API.
- [ ] Create form: name, colors (with preview), mode; image style shown as auto-derived
      (read-only); keywords input with the guard rules surfaced.
- [ ] Edit/archive for custom palettes; roots shown read-only.
- [ ] **Drift gate retargeted (G6):** `check-palette-drift.mjs` narrows to the still-static
      surface (image presets / root keys) or asserts the FE consumes the API dynamically;
      its AE-0180 rule-fires test updated.
- [ ] **Co-deploys with AE-0270** (flag flips on in the same release).
- [ ] i18n: roots keep en/pt labels; custom palettes show their single user-typed name (O3).
- [ ] FE design reviewed via `impeccable`.

**Risks:** the P3→P4 blind window (mitigated by co-deploy). **`.feature` required.**

---

## Dependency graph & suggested order

```
AE-0268 (P1, ships alone, prod migration)
        └─> AE-0269 (P2, persistence + resolver + snapshot)
                    ├─> AE-0270 (P3, CRUD API, flag OFF) ─┐
                    └─> AE-0271 (P4, FE catalog) ─────────┴─> co-deploy (flag ON)
```

1. **AE-0268** first and **alone** — isolates the risky prod DB migration; merge during a
   calm window (auto-deploys prod).
2. **AE-0269** — backend foundation; no user-visible change yet.
3. **AE-0270 + AE-0271** — build in parallel, **co-deploy** (flag gates the cutover).

## Epic-level risks

- **Prod DB migration** (AE-0268) on a historically-drifted DB — census gate + staging
  trial + roll-forward.
- **Resolver reliability** (AE-0269) — cache + registry-only fallback + degraded-mode AC.
- **Abuse / cost** (AE-0270) — hex validation, keyword guards, rate-limits; snapshot (D9)
  removes the mass-re-render fan-out.
- **Coordination** (AE-0270/0271) — must co-deploy; feature flag is the safety valve.

## Handoff

→ `/ticket-writer-skill` to materialize `.agent/tasks/AE-0267.md` (epic) +
AE-0268..0271 from this breakdown (ACs, Gherkin scenarios, QA checklists).
→ `/architect-skill validate` per ticket before Ready (esp. AE-0268 migration).
→ `impeccable` for AE-0271 visual design.
