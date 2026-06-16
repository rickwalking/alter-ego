# QA Report — Phase 6 Wave C (AE-0128 + AE-0129)

**Verdict: PASS** — converged over 2 consecutive external-QA rounds (PASS → PASS). Gate spine green
locally (mypy 498, ruff clean, lint-imports 19/0, vulture clean, arch-ratchet PASS with get_container at
baseline 14, AE-0125 safety net 31/31 diff=0); check-integrity 0 blockers; no suppressions, no per-file-ignore/
threshold changes, no `.importlinter` edits.

## Scope
- **AE-0128** — public visibility (is_public) + scheduling behind publishing ports; carousel publish via a
  release command + ACL; standalone blog publish/unpublish/schedule via visibility/schedule ports.
- **AE-0129** — distribution (Instagram publish + caption read) behind a DistributionPublisher channel port;
  the Meta Instagram publisher becomes an adapter.

Behavior-preserving: the LegacyPublishingAcl is the only publishing code touching the carousel/blog ORM /
channel SDK; application + domain depend only on Protocols. The release command replicates crud.py's publish
preconditions exactly (no auto-publish change). Byte-identical responses proven by the AE-0125 safety net.

## Rounds
- **Round 1 — PASS** (5 LOW). Actionable items closed: removed the premature LinkedIn-read path
  (`read_linkedin_posts` / `linkedin_posts_for` / `Publication.linkedin_post_{pt,en}` had no route consumer —
  mirrors the AE-0126 discipline of shipping a port only with its consumer); corrected an overclaiming
  bootstrap docstring (the scheduled-publish worker still constructs the service directly).
- **Round 2 — PASS** (5 LOW, all acceptable: the blog-edge carousel-repo session is harmless/unused on the
  blog path and proven byte-identical by the safety net; unit tests use mocks but the integration safety net
  exercises the routes; a residual LinkedIn doc mention was cleaned; the BlogPostRepository re-export is a
  pre-existing AE-0126 shim, out of scope).

## Evidence
- ORM-write typing fixed via SQLAlchemy 2.0 `Mapped[]` (no overrides). No new `get_container()` (locator
  ratchet held at 14). No new application→infra / api→infra import pairs. Deterministic-stub channel tests
  (no live key). check-integrity: no net-new gaming.
