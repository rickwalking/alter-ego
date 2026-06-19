# Kaizen Report — session-2026-06-18c
Mode: session | Generated: 2026-06-18 | Signal window: learnings-log records 3–4

Signal: `.agent/reports/kaizen-session-2026-06-18c.signal.md`
Invariant: every proposal ratchets the bar **UP or HOLD**. No down-ratchets present.

## Proposals (ranked)

### P1 — Make board-mutating ticket tooling resilient + test-cover it  [ratchet: UP] [T2]
**Failure class:** FC-1.
**Root cause (5-whys):** AE-0223 gitignored + `git rm`'d `.agent/BOARD.md`, but
`add_to_board` (create_ticket.py:40) and `update_board` (move_ticket.py:83) still
`read_text()` it unconditionally → `FileNotFoundError`. The CI gate
`pytest tests/unit/agent_tasks/` exists but never exercises these two functions or
the absent-board path, so the regression shipped invisibly. *Why untested?* The
suite was grown ticket-by-ticket (schema, scaffold_dev_summary) and board mutation
was never the subject of a ticket.
**Enforcement (the fix the test demands):**
- `add_to_board` / `update_board`: when `BOARD.md` is absent, **regenerate it via
  `render_board.main()` first** (the board is a generated view), then mutate — or
  no-op cleanly if regeneration is unavailable. Never crash on the gitignored file.
- Add `backend/tests/unit/agent_tasks/test_create_ticket.py` and extend
  `test_move_ticket.py`: cover `next_ticket_id`, `add_to_board`/`update_board` with
  **board present AND board absent** (the seeded regression: assert the absent-board
  call no longer raises). These run in the existing `agent-ticket-hygiene.yml` gate.
**Exact files:** `scripts/agent_tasks/create_ticket.py`,
`scripts/agent_tasks/move_ticket.py`, `backend/tests/unit/agent_tasks/test_create_ticket.py` (new),
`backend/tests/unit/agent_tasks/test_move_ticket.py`.
**Seeded-violation proof:** the new absent-board tests FAIL on today's code, PASS after the fix.
**Eliminates:** the OPEN top-priority bug blocking PR #54; the whole "gitignore
decision silently broke the delivery workflow" class.
**Note:** must land on the wave branch (`feat/dev-wave-ae0220-0227`) BEFORE PR #54 merges.

### P2 — Promote the duplicate-ticket-ID warning to a BLOCKING gate  [ratchet: UP] [T1]
**Failure class:** FC-2.
**Root cause:** `next_ticket_id` allocates from the local tree only; unmerged-branch
IDs collide on re-branch. `_warn_duplicate_ids` (AE-0181) sees the collision but only
prints a WARNING — so nothing fails. Happened twice (AE-0145..0148 rename; AE-0228
near-miss).
**Enforcement:** make duplicate IDs a **blocking** error in
`validate_all_tickets.py` (exit 1). On a `pull_request` run, GitHub checks out the
merge ref, so a branch whose new IDs collide with `main` fails the
`agent-ticket-hygiene` gate **before merge** — exactly the AE-0145..0148 case.
**Exact files:** `scripts/agent_tasks/validate_all_tickets.py` (promote
`_warn_duplicate_ids` to a blocking check; keep the actionable message), a
seeded-violation test under `backend/tests/unit/agent_tasks/`.
**Seeded-violation proof:** two ticket files sharing one `AE-####` → validator exits 1.
**Tradeoff (must be weighed at approval):** AE-0181 deliberately kept this
non-blocking ("renumbering tracked separately"). Promoting it means a PR with a
transient/legit duplicate is blocked until renumbered. Given 2 real collisions and a
clear remediation message, the ratchet is justified — but this contradicts a prior
deliberate decision, so it is the item most worth the external skeptical pass.
**Optional hardening (same ticket or follow-up):** teach `next_ticket_id` to also
consult `git ls-tree`/branch refs for the max ID. Heavier and branch-state-dependent;
the blocking gate is the primary, sufficient enforcement.
**Eliminates:** silent ID collisions + manual renumber toil.

### P3 — gates.sh preflight: distinguish "tool not installed" from a real violation  [ratchet: HOLD→UP] [T1]
**Failure class:** FC-3.
**Root cause:** missing `jscpd`/`knip` binaries exit 127; `gates.sh` surfaces this as
a raw failure indistinguishable from a real finding, so a clean tree reads as broken.
**Enforcement:** a small preflight in `scripts/ci/gates.sh` that, for frontend gates
depending on local devDeps, checks the binary is resolvable and emits an actionable
`devDependency '<tool>' not installed — run \`cd frontend && npm ci\`` message with a
**distinct, non-PASS exit** (a missing tool must never be rounded up to PASS — this
HOLDs the bar while improving signal fidelity).
**Exact files:** `scripts/ci/gates.sh`.
**Seeded-violation proof:** simulate a missing binary (PATH shim) → gate prints the
actionable message and does not report PASS.
**Eliminates:** recurring wasted time + the risk of misreading a real failure as "just env".

## Rejected / no-ticket (transparency)
- **FC-4 (scan false findings):** NO new ticket. The Phase 3.6 external-skeptical
  standard + "verify scan claims against live code" already exist and the architect
  applied them this session (caught both false findings). Enforcement already in place.
- **No down-ratchet proposals** were generated or considered.

## Recommended order
P1 (clears the open bug + highest blast radius) → P2 (cheap, high-recurrence) → P3 (cheap quality-of-life).

## Phase 3.6 — External skeptical (opencode cold-critic)
Verdict **WARN**. Report: `.agent/reports/kaizen-session-2026-06-18c.skeptical-review.md`.
All findings verified against live code (advisory, not authoritative) and resolved in
the ticket Decision Logs. Material outcomes folded into the tickets:
- P1: atomic board writes (TOCTOU) + tmp_path-isolated tests + land-first constraint.
- P2: documented parallel-PR merge-ref residual + git-ref-aware allocator (root cause)
  + precise 0→1 seeded test. (Bumped T1→T2 for the allocator work.)
- P3: return `EXIT_SKIP` (77) not FAIL; probe `node_modules/.bin/<tool>` not `which`.
- P4: per-file repo-wide reference proof before deletion (knip is heuristic); barrel
  policy split out into a new P5.

## Tickets created (approved + critic-amended)
- **AE-0237** — Board-mutating tooling regenerate-or-noop + tests  (P1, T2) — clears the OPEN bug
- **AE-0238** — Block duplicate ticket IDs + git-ref-aware allocator  (P2, T2)
- **AE-0239** — gates.sh preflight: missing tool → SKIP not FAIL  (P3, T1)
- **AE-0240** — Delete ~9 verified-dead frontend files (proof-gated)  (P4, T2)
- **AE-0241** — Decide + document barrel-import policy  (P5, T1)

All created on branch `chore/kaizen-018c-tooling-tickets` (off HEAD @ AE-0236 to avoid
the ID collision the local-only allocator would otherwise cause). `validate_all_tickets`
→ All 236 OK.

## Verification findings (no ticket emitted — for human decision)
- **Suspense/fetch coverage:** AE-0228/0229/0230 DO cover the genuine ~2–3 ADR-010
  Suspense violations + the admin raw-`fetch` cluster + login + carousel exception.
  BUT a live scan shows additional client *pages* with raw `fetch` —
  `app/dashboard/personas/page.tsx`, `app/dashboard/rubrics/page.tsx`,
  `app/dashboard/workflow/page.tsx` — not explicitly named in AE-0228..0230. The
  existing ESLint fetch rule (AE-0184) only blocks `fetch(` under `src/**/hooks/**`,
  not pages, so these are untracked. **Recommend** folding them into AE-0229/0230 scope
  or a small follow-up. Flagged to the user, not auto-ticketed.
