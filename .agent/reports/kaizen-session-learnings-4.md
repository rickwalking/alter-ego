# Kaizen Report — session-learnings-4 (2026-06-17)
Mode: sweep (retrospective) | Scope: executing the production-readiness sweep (AE-0189..0202)

## This pass
Executed all 14 production-readiness tickets via dev→QA subagents across 4 buckets
(docker, repo, docs, frontend lint). 12 DONE, 2 PARTIAL (AE-0191 visual export,
AE-0202 1 backend-variable img). Integrity 0 blockers, eslint 0 errors, 884 FE tests pass.

## Learning Classes (ranked)

| # | Learning | Evidence | Severity |
|---|----------|----------|----------|
| L1 | **Building the prod image catches latent runtime crashes that no test does.** `jinja2` was an undeclared runtime dep (reachable only via dev-only `diff-cover`); under `--no-dev` the prod image crashes on `import rag_backend.main` (ModuleNotFoundError). Found only by actually building. | AE-0190 | **Critical** |
| L2 | Docker layer hygiene: a trailing `chown -R /app` duplicated the venv+browser tree into a 1.18GB layer (2.83→1.65GB). Use `COPY --chown=`. | AE-0190 | High |
| L3 | Config rot: the eslint `no-img-element` exemption glob pointed at `src/features/...` after code moved to `src/modules/publishing/...` — a dead override silently exempting nothing. | AE-0202 | Med |
| L4 | Per-rule warn→error promotion works where blanket flips fail: 4 rules promoted cleanly; 2 left unforced (legit cases). | AE-0199..0202 | Info |

## Proposals (for human review — NOT auto-created)
- **K1 (real-bug-class enforcement):** add a CI gate that does `uv sync --no-dev` + `python -c "import rag_backend.main"` (or builds the backend image) to catch undeclared runtime deps before prod. This would have caught the jinja2 crash. Highest-value follow-up.
- **K2:** a periodic "config-rot" check that flags eslint `files:`/override globs matching zero files (catches L3-class dead config after restructures).
- **K3:** optional `dive --ci` image-efficiency gate to catch L2-class layer bloat.

## Rejected (would loosen): none.
