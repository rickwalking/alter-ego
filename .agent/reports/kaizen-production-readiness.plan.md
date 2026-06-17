# Kaizen Report — production-readiness (2026-06-17)
Mode: sweep | Architect web-research | Scope: docker, repo structure, dead code, docs, frontend lint

## Headline findings (measured/verified, not assumed)
- **Docker backend image** is the real bloat: SINGLE-stage, ships Playwright Chromium (~400-700MB) + uv/build toolchain in runtime, and `context: .` with **no root .dockerignore** uploads ~1.2GB (incl. frontend/node_modules) every build. Frontend image already good (3-stage, alpine, standalone).
- **"Extra rag_backend folder" = standard src-layout** (correct, keep). Only genuine stray: `backend/main.py` (uv-init stub, referenced nowhere).
- **knip already shipped** (AE-0152 export gate live; AE-0158 dead-file = Intake; AE-0183 dep gate = Review). Don't re-create — finish them.
- **jscpd well-calibrated** (0.75% vs 0.80% threshold, tests excluded). Do NOT ratchet down now (no headroom).
- **eslint warn→error**: a blanket flip is wrong (AE-0188) — but a PER-RULE ratchet is available: 7 promotable now, ~46 after small fixes, ~192 correctly stay warn.

## Proposals (ranked; ratchet UP unless noted)

### Docker / production (headline)
- **D1 — root `.dockerignore`** [UP/T1] fixes the 1.2GB build-context bug (backend builds with `context: .`). Biggest build-time/transfer + hygiene win.
- **D2 — backend multi-stage** [UP/T2] builder installs deps; runtime copies only `.venv`, drops uv/pip, `CMD` → direct `uvicorn`. ~80-150MB.
- **D3 — slim Playwright** [UP/T2, risk:med] chromium-only + `--with-deps` in one RUN + `apt clean`; evaluate `chromium-headless-shell`. ~150-300MB. **Verify carousel export visually.**
- **D4 — BuildKit cache mounts** [UP/T1] `--mount=type=cache` for uv sync + npm ci → faster droplet rebuilds.
- (Rejected: distroless backend — Chromium needs apt/system libs; risk ≫ benefit.)

### Repo structure / cleanup
- **S1 — delete stray `backend/main.py`** [UP/T1] uv-init stub, unreferenced (real entrypoint is `rag_backend.main`).
- **S2 — root cleanup** [UP/T1] `git rm` ~7MB screenshots (carousel-*.png, slide-1-check.png) + 10 Playwright a11y snapshots (create-page, login-*, langfuse-*) + stale `tmp/`; close `.gitignore` gaps. KEEP `clickhouse-config/` (live Langfuse mount).
- **S3 — root `Makefile`/`just`** [UP/T1-2] unified `setup/build/test/lint/typecheck` delegating to uv + npm. (Rejected: npm/pnpm workspaces / Nx / Turborepo — JS-only, won't unify Python; over-engineering.) KEEP src-layout.

### Dead code / docs
- **DC1 — finish AE-0158** (dead-file advisory) — 21 unused files (dead barrels + orphan persona components). EXISTING (Intake).
- **DC2 — finish AE-0183** (dep gate) — add config-only-devDep allowlist (6 knip false positives) + list `postcss`. EXISTING (Review).
- **DC3 — fix 1 real knip finding** [UP/T1] duplicate-value exports in `frontend/src/constants/neon.ts`.
- **DO1 — docs cleanup** [UP/T1] DELETE 11 noise/superseded docs; add `Status: Done` to phase-1..6 plans.
- **DO2 — docs index + deprecate** [UP/T2] `docs/README.md` index (kills orphan signal); mark ~21 superseded; UPDATE 2 stale-but-useful (security, agentic impl).

### Frontend lint warn→error (the user's ask — per-rule, suppression-free)
- **L1 — promote `no-non-null-assertion` → error NOW** [UP/T1] all 7 are in tests; add `off` in test override → pure ratchet, zero churn.
- **L2 — promises-hygiene** [UP/T2] fix 16 `no-floating-promises` + 14 `no-misused-promises` (mechanical, behavior-preserving), then flip BOTH to error.
- **L3 — `max-params` → error** [UP/T1] refactor 2 sites to options objects, then flip.
- **L4 — `no-img-element` → error** [UP/T2] fix the DEAD exemption glob (`features/` → `modules/publishing/`), migrate 7 `<img>`→`next/image`, then flip.
- jscpd: keep threshold 0.8 (calibrated); optional cosmetic `format`/ignore tidy.

## Rejected (would loosen or force suppressions — INVARIANT)
- ❌ Blanket eslint warn→error (forces eslint-disable on the 192 legit guards — AE-0188).
- ❌ Promote `no-unnecessary-condition` / `prefer-nullish-coalescing` (legit runtime guards / intentional `||`).
- ❌ Ratchet jscpd threshold down now (no headroom — would put gate underwater).
- ❌ Flatten src-layout; npm workspaces; distroless backend.

## Overlap note
knip export gate = AE-0152 (done); dead-file = AE-0158; dep gate = AE-0183. New tickets start at AE-0189.
