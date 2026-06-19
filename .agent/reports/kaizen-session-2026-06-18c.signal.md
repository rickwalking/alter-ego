# Kaizen Signal — session-2026-06-18c
Mode: session | Generated: 2026-06-18 | Signal window: learnings-log records 3–4 (watermark 2026-06-18T19:14:30 → 2026-06-18T20:33:41)

Source: `.agent/handoff/learnings-log.jsonl` records 3 (dev-wave/kaizen) and 4
(architect-plan + found bug). Both verified against live code before clustering.

## Failure Classes (ranked by frequency × severity)

| # | Class | Freq | Severity | Gate that should catch it | Status |
|---|-------|------|----------|---------------------------|--------|
| FC-1 | **Board-mutating ticket tooling is untested + brittle to the gitignored board** — `add_to_board` (create_ticket.py:40) and `update_board` (move_ticket.py:83) `read_text()` the now-gitignored `.agent/BOARD.md` unconditionally → `FileNotFoundError`. AE-0223 shipped this; QA missed it. | 1 incident, repo-wide blast radius (breaks ALL ticket create/move on main) | HIGH | `pytest tests/unit/agent_tasks/` exists + runs in CI (`agent-ticket-hygiene.yml`) but covers only `schema` + `scaffold_dev_summary` — never `add_to_board`/`update_board`/`next_ticket_id` | OPEN (workaround: `make board`) |
| FC-2 | **Ticket-ID allocation is branch-local → collisions across unmerged branches** — `next_ticket_id` globs only the local working tree; IDs living on an unmerged branch get re-allocated when branching off main. | 2 (AE-0145..0148 collided → renamed 0224..0227; AE-0228 near-miss) | MED-HIGH | `validate_all_tickets._warn_duplicate_ids` (AE-0181) detects dupes but is **WARNING-only, non-blocking by design** | recurring |
| FC-3 | **Local gate parity friction — missing frontend devDeps misread as failures** — `jscpd`/`knip` not installed locally → exit 127; `gates.sh` has no preflight to distinguish "tool missing (env)" from a real violation. | recurring (this session + standing landmine) | LOW-MED | a `gates.sh` tool-availability preflight (none exists) | workaround (`npm ci` / `npx jscpd@4`) |
| FC-4 | **Explore/scan false findings flow into plans** — "ADR-011/012 missing from CLAUDE.md" (false; they're indexed) and "isLoading everywhere" (overstated; mostly legit mutation flags). | 2 this session | LOW | already covered by the Phase 3.6 skeptical-validation standard + architect verified vs live code | already-mitigated |

## Notes for synthesis
- FC-1 and the handoff's TOP-PRIORITY open bug are the **same** item — the kaizen
  framing (untested + brittle tooling) yields the durable fix *and* clears the bug
  blocking PR #54.
- FC-2's detector already exists; the ratchet is "promote WARNING → blocking gate",
  not "build new detection". The AE-0181 author deliberately left it non-blocking
  ("renumbering tracked separately") — that decision is now contradicted by 2 real
  collisions, so the tradeoff is re-litigated in the plan (P2).
- FC-4 needs no new ticket — the existing skeptical gate is the enforcement;
  recorded here for transparency.
