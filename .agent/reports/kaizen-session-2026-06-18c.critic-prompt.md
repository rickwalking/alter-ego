ROLE
You are an adversarial architecture reviewer (devil's advocate). You are NOT the author.
Your job is to find material risks, false assumptions, and gaps — not to validate the plan.

LIMITS
- Do NOT say "looks good", "solid plan", or equivalent unless zero material findings exist.
- You MUST produce at least 3 material concerns. If fewer exist, state what evidence is missing.
- Challenge the STRONGEST version of the plan, not a strawman.
- Distinguish "bad idea" vs "incomplete because …" (prefer the latter).
- No implementation code. No scope expansion unless tied to a stated risk.
- Cite uncertainty explicitly; do not invent project facts not in the packet.

LENSES (apply each briefly): Security/abuse · Data integrity & migration · Operational failure (deploy/rollback/observability) · Concurrency/consistency · Cost & complexity · Testability & missing edge cases

OUTPUT (mandatory markdown):
# Cold Critic Review
## Verdict
BLOCK | WARN | PROCEED_WITH_CAUTION
## Findings
### [BLOCKER|WARN|INFO] <title>
- Assumption / Risk / Impact / Suggested mitigation / Open question for author
## Missing evidence
## Residual risks if plan proceeds unchanged

================================================================
PACKET — four proposed process/quality enforcement changes to a full-stack repo
(Python FastAPI backend + Next.js frontend) with an agentic ticket workflow under
`.agent/tasks/AE-####.md`. Review each independently.

## Repo facts (verified against live code)
- Tickets are plain markdown files `.agent/tasks/AE-NNNN-*.md`. A python tool
  `create_ticket.py` allocates the next id by globbing `AE-*.md` in the LOCAL working
  tree and taking max+1. `move_ticket.py` changes a ticket's Status.
- A generated kanban view `.agent/BOARD.md` was recently gitignored + git-rm'd. But
  `create_ticket.add_to_board()` and `move_ticket.update_board()` still call
  `board_path.read_text()` unconditionally → `FileNotFoundError` when the file is
  absent (i.e. on any fresh clone / CI / post-merge). A separate `render_board.py`
  regenerates the board from the ticket files.
- CI gate `agent-ticket-hygiene.yml` runs `pytest tests/unit/agent_tasks/` and
  `validate_all_tickets.py`. Existing tests cover only `schema` + one move_ticket
  helper; they never exercise `add_to_board`/`update_board`/`next_ticket_id`.
- `validate_all_tickets.py` has `_warn_duplicate_ids()` that PRINTS a warning when two
  files share an `AE-####` id, but does NOT fail (exit 0). It was deliberately left
  non-blocking by an earlier ticket (AE-0181) whose stated reason was "renumbering is
  tracked separately". Duplicate-id collisions have since occurred twice because ids
  live on unmerged branches that the local max+1 allocator can't see.
- `scripts/ci/gates.sh` runs frontend gates that shell out to `jscpd` and `knip`.
  When those binaries are absent locally they exit 127; the gate surfaces a raw
  failure indistinguishable from a real violation. CI installs them via `npm ci`.
- `knip` reports 21 "unused" frontend files: ~9 appear genuinely dead (a stray
  provider, 2 unused constants files, 3 unused schema files, a test fixture, 2 empty
  post-migration type barrels); 2 are design-system re-export barrels
  (`components/atoms|molecules/index.ts`) bypassed by ~128 direct imports; ~5 are
  intermediate module barrels (bounded-context pattern) re-exported via parent
  barrels; and a `personas/` route's files are flagged but the route is still live.

## Proposal P1 — make board-mutating tooling resilient + add tests [T2]
Change `add_to_board`/`update_board`: when `BOARD.md` is absent, regenerate it via
`render_board` then mutate (or no-op cleanly), never crash. Add unit tests covering
those functions with the board present AND absent (the absent-board test fails on
today's code, passes after the fix). Tests run in the existing CI gate.

## Proposal P2 — promote duplicate-ticket-id detection from WARNING to BLOCKING [T1]
Make `validate_all_tickets.py` exit 1 when two files share an `AE-####` id. On a
GitHub `pull_request` run the merge ref is checked out, so a branch whose new ids
collide with main fails the gate before merge. Reverses AE-0181's deliberate
non-blocking choice. Add a seeded two-file-same-id test that asserts exit 1.

## Proposal P3 — gates.sh preflight distinguishing "tool not installed" from a real violation [T1]
Add a preflight that checks `jscpd`/`knip` are resolvable; if not, emit an actionable
"run `cd frontend && npm ci`" message with a distinct, non-PASS exit (a missing tool
must never be rounded up to PASS).

## Proposal P4 — delete the ~9 genuinely-dead frontend files + decide the barrel policy [T2]
Delete the ~9 dead files. For the 2 design-system barrels and ~5 module barrels,
either configure them as knip `entry` points or migrate consumers to import via the
barrel — a one-time convention decision. The knip dead-file gate is currently advisory
(non-blocking).

## Cross-cutting question
These four ride on top of TWO already-open, unmerged, STACKED PRs (#54 carrying the
gitignore-board change that caused P1's bug; #55 stacked on #54). Merging the base PR
auto-deploys production. Is the sequencing safe? What ordering/landing constraints or
hidden coupling could bite?
