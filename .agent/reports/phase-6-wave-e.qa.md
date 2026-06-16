# QA Report — Phase 6 Wave E (AE-0132 publishing exit gate)

**Verdict: PASS** — CI/docs-only exit gate. Converged over 3 external-QA rounds.

## Convergence
- r1 PASS (3 LOW) — a doc-accuracy nit (read_projection_helpers imports the BlogPostModel type vs the
  "two ACL seams" claim) was over-corrected with an ORM-free runtime refactor.
- r2 FAIL (CRITICAL, scope) — correctly flagged that the runtime refactor violated AE-0132's "CI/docs only,
  no runtime change" scope. Reverted the refactor; instead reworded §13a to accurately state the two ACL seams
  own all ORM access while read_projection_helpers references only the model type (no ORM access).
- r3 PASS (4 LOW, all acceptable/by-design: contract scopes application/domain by design; the 2bbec20→cddd85b
  churn is net-clean; the demonstrate+revert evidence is recorded in this report + §13e).

## Deliverable
3 publishing contracts (application-isolation / public-facade / no-editorial-presentation), regenerated
.importlinter (22 kept / 0 broken), AE-0082 baseline ratcheted DOWN (application->infra 63->62, api->infra
79->76; get_container 14, commit-sites 9), module-conventions §13 worked example + the consent-gated AE-0133
deferred auto-publish cutover + embedded-column drop. Each contract falsified by a reverted violation.

## Gates
lint-imports 22/0, arch-ratchet PASS, ruff clean, mypy 501, vulture clean, gates.sh 14 PASS / 0 FAIL / 3 SKIP
(mutation PASS), check-integrity 0 blockers. No runtime behavior change; no suppressions; no contract weakened.
