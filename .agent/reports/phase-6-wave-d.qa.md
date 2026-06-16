# QA Report — Phase 6 Wave D (AE-0131 read-model projections)

**Verdict: PASS** — converged over 4 external-QA rounds. The public carousel /blog (+lang), content-calendar,
workflow-board, and editorial-analytics serve from publishing read-model projections behind the facade; blog
CRUD routes are thin adapters. A single read ACL is the only publishing ORM read seam.

## Convergence
- r1 PASS (6 LOW) — added a per-field backfill-fallback unit test.
- r2 PASS (2 MEDIUM coverage + 5 LOW) — added an HTTP-level backfill-row parity test (production path).
- r3 caught a real byte-identity edge: the /blog 404 gate had moved off the legacy project.blog_markdown
  signal. Fixed to key on project.blog_markdown unconditionally (a backfill row can never flip a legacy 404);
  added an orphan-row 404 regression test.
- r4 PASS (4 LOW, all by-design/acceptable).

## Byte-identity evidence
AE-0125 safety net 32/32 diff=0; the carousel-blog projection prefers the AE-0127 backfill row and falls back
per-field to embedded columns (proven identical by the HTTP parity test, since AE-0127 sets content.markdown=
blog_markdown, title=title-or-topic, excerpt NULL). Calendar/analytics delegate to the legacy services (exact
aggregation reuse). i18n reads embedded translations only (identical to legacy).

## Gates
mypy 501, ruff clean, lint-imports 19/0, vulture clean, arch-ratchet PASS (api->infra 79->76, get_container 14),
check-integrity 0 blockers, broad regression 769 passed. No suppressions, no per-file-ignore/threshold changes.
