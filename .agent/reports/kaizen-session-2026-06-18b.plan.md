# Kaizen Report — session-2026-06-18b
Mode: session | Signal window: learnings newer than `2026-06-18T17:20:00-03:00`
Signal report: `.agent/reports/kaizen-session-2026-06-18b.signal.md`

## THE INVARIANT — ratchet UP, never down
No proposal below loosens a threshold, adds a suppression, or weakens a gate.
Notably, FC2's fix is **documenting** the commitlint convention, **not** relaxing
`subject-case` (that would be a DOWN-ratchet — rejected by construction).

## Proposals (ranked)

### P1 — Serialize prod deploys with a `concurrency:` group  [ratchet: UP] · T1 · Cross-cutting
- **Failure class:** FC4 — two merges within ~30s spawned two concurrent
  `deploy.yml` runs against the same DigitalOcean droplet (both succeeded, but
  they can race: interleaved `.env` rewrite, half-applied image swap, migration races).
- **Root cause:** `deploy.yml` triggers `on: push` to main with **no concurrency control**.
- **External best practice:** GitHub Actions `concurrency:` with a stable group +
  `cancel-in-progress: false` (queue, don't cancel — a started prod deploy must finish,
  the next runs after). This is the canonical single-flight-deploy pattern.
- **Enforcement (exact files):**
  - `.github/workflows/deploy.yml` — add top-level:
    ```yaml
    concurrency:
      group: prod-deploy
      cancel-in-progress: false
    ```
- **Expected signal eliminated:** no more concurrent/racing prod deploys; merges
  queue safely instead of needing manual staggering.
- **AE-0180:** N/A (no static-analysis rule added). Acceptance proof = a workflow
  lint / a documented dry-run showing serialization, plus the YAML key present.

### P2 — CI gate: `BOARD.md` must match the branch's tickets  [ratchet: UP] · T2 · Cross-cutting
- **Failure class:** FC3 — branching a task off `origin/main` while tickets lived
  only on an unmerged branch, then running `render_board.py`, produced a regressed
  `BOARD.md` (missing AE-0216's card) that nearly got committed.
- **Root cause:** `BOARD.md` is a **committed generated artifact** derived from
  `.agent/tasks/*`, with no check that the committed copy matches the tickets
  present on the current branch.
- **Fix:** add a gate that re-renders the board from the branch's own tickets and
  fails if the committed `BOARD.md` differs (stale/regressed). It compares only to
  tickets present on the branch, so it does not false-positive on mid-flight work.
- **Enforcement (exact files):**
  - new check in `scripts/ci/gates.sh` (or a small `scripts/ci/check-board-fresh.sh`)
    that runs `render_board.py --check` (add a `--check` mode that renders to a temp
    buffer and diffs against `.agent/BOARD.md`, exit non-zero on drift).
  - wire it into the existing CI gate aggregator (`ci-gate`).
- **AE-0180 (mandatory):** ship a rule-fires test — seed a ticket whose Status
  changed without re-rendering, assert the gate exits non-zero. Exemplar pattern:
  `frontend/src/scripts/use-client.test.ts`.
- **Alternative considered:** stop committing `BOARD.md` (gitignore + generate on
  demand) — removes the class entirely but loses GitHub-viewable board; larger
  change. Recommend the freshness gate; flag the alternative for the ticket's
  design discussion.

### P3 — Document the commitlint lowercase-subject convention  [ratchet: HOLD] · T1 · docs
- **Failure class:** FC2 — uppercase ticket IDs (`AE-0216`) in commit subjects trip
  commitlint `subject-case`; recurs every session that commits a ticket-id subject.
- **Root cause:** the convention lives only in memory/handoff landmines, not in
  CLAUDE.md where authors look.
- **Fix (NOT a loosening):** add a one-liner to CLAUDE.md → Git & Commits:
  "commitlint `subject-case` forbids upper/start/pascal/sentence case — keep the
  whole subject lowercase, including ticket IDs (e.g. `move ae-0216 ticket to review`)."
- **Enforcement (exact files):** `CLAUDE.md` (Git & Commits section).
- **AE-0180:** N/A (doc; commitlint already enforces — we add no new rule).

### P4 — Make `Invalid status` self-documenting + document the entry state  [ratchet: HOLD/UP] · T1 · backend
- **Failure class:** FC1 — `Status: Todo` rejected; the valid entry state `Intake`
  (and the full status set) is undiscoverable.
- **Root cause:** `schema.py` emits `Invalid status: {x}` with no enum hint; statuses
  undocumented in CLAUDE.md / agentic-delivery-system.md.
- **Fix:**
  - `scripts/agent_tasks/schema.py` — change both `Invalid status:` messages to list
    `ALL_STATUSES` and note "new tickets enter at `Intake` (`Ready` is T0-only)".
  - `docs/plans/agentic-delivery-system.md` — add the status lifecycle line.
- **Enforcement (exact files):** `schema.py`, `docs/plans/agentic-delivery-system.md`.
- **AE-0180:** small unit test asserting the error string includes the valid options
  (tooling test, not a static-analysis rule). Could bundle with P3 as one
  "developer-ergonomics" ticket if you prefer fewer tickets.

## Rejected (would loosen the bar)
- *Relax commitlint `subject-case` to allow uppercase ticket IDs* — DOWN-ratchet;
  rejected. P3 documents the convention instead.

## Ratchet summary
| P | Direction | Effort | Area |
|---|-----------|--------|------|
| P1 | UP | T1 | Cross-cutting (CI/deploy) |
| P2 | UP | T2 | Cross-cutting (CI gate) |
| P3 | HOLD | T1 | docs |
| P4 | HOLD/UP | T1 | backend/docs |

## Phase 3.6 — External cold-critic (P2)
Ran the blind P2 packet through the architect cold-critic (opencode). Verdict:
**BLOCK**. Review saved to `kaizen-session-2026-06-18b.skeptical-review.md`.
Verified each finding against live code:
- **Finding 1 (BLOCKER) — CONFIRMED.** The proposed gate is an *inverse detector*:
  `render_board.py` rebuilds the board from current-branch tickets, so a developer
  who re-renders on a branch missing tickets and commits the regressed board passes
  the `--check` (in-memory render == committed board, both regressed). The gate
  catches "forgot to re-render" (stale), not the actual incident (regressed).
- **Finding 2 (BLOCKER) — CONFIRMED plausible.** A branch whose inherited `BOARD.md`
  references tickets with no `.md` on that branch would FAIL the gate on unrelated PRs.
- **Finding 3 (WARN) — REFUTED.** A committed regressed `BOARD.md` is itself under
  `.agent/**`, so it trips the `ci-gate` path filter and runs `agent-gate`. No gap.

**Decision:** P2 as specified is NOT emitted. Re-scope required (anchored-diff vs
gitignore) — pending user direction.

## Tickets created (approved + unaffected)
- AE-0220 — P1: Serialize prod deploys with a concurrency group in deploy.yml (T1)
- AE-0221 — P3: Document commitlint lowercase-subject convention in CLAUDE.md (T1)
- AE-0222 — P4: Make invalid-status error self-documenting + document lifecycle (T1)
- AE-0223 — P2 (re-scoped): Stop committing generated BOARD.md; gitignore + render on demand (T1)
  — replaces the BLOCKED freshness-gate; user chose the gitignore approach.
