# In-flight ticket index (by stream + branch)

**Snapshot date:** 2026-06-18 — **verify against git** before acting; statuses and branch
mapping drift as tickets move. Regenerate by re-reading `.agent/tasks/AE-02*.md` +
`git log --diff-filter=A`.

> ⚠️ **Auto-deploy:** merging anything to `main` triggers a full prod redeploy
> (`.github/workflows/deploy.yml`). None of the tickets below are on `main` yet
> (main's max is AE-0219).
>
> ⚠️ **Stacked branches — landing order matters.** These four branches form a single
> stack (base → top). The current branch `chore/agent-restructure-epic-tickets` is the
> TOP, so its working tree already contains every ticket file from all ancestor branches.
> Merge base-first (#54 before #55, etc.) or you will create conflicts / orphaned diffs.

Branch-of-origin below is the **earliest** stack branch whose history contains the file's
adding commit (verified via `git merge-base --is-ancestor`).

---

## Stream: Frontend data-layer (Suspense / fetch / knip)

| AE-# | Title | Tier | Status | Branch (PR) |
|------|-------|------|--------|-------------|
| AE-0228 | Admin module TanStack Query layer + migrate admin user management | T2 | Intake | chore/frontend-docs-plan-tickets-v2 (PR #55) |
| AE-0229 | Migrate remaining initial-load components to Suspense | T2 | Intake | chore/frontend-docs-plan-tickets-v2 (PR #55) |
| AE-0230 | Login mutation hook + document carousel image-download fetch exception | T1 | Intake | chore/frontend-docs-plan-tickets-v2 (PR #55) |
| AE-0240 | Delete verified-dead frontend files surfaced by knip | T2 | Intake | chore/kaizen-018c-tooling-tickets (no PR) |
| AE-0241 | Decide + document barrel-import policy (knip entry vs barrel) | T1 | Intake | chore/kaizen-018c-tooling-tickets (no PR) |

Done vs pending: 0 done / 5 pending (all Intake).

## Stream: Docs reorg

| AE-# | Title | Tier | Status | Branch (PR) |
|------|-------|------|--------|-------------|
| AE-0231 | Documentation reorganization and cleanup (epic) | T3 | Intake | chore/frontend-docs-plan-tickets-v2 (PR #55) |
| AE-0232 | Docs quick wins: status headers + ADR-0009 accepted | T1 | Intake | chore/frontend-docs-plan-tickets-v2 (PR #55) |
| AE-0233 | Delete/archive superseded docs with inbound-link checks | T2 | Intake | chore/frontend-docs-plan-tickets-v2 (PR #55) |
| AE-0234 | Docs folder indexes + plans active/historical split | T2 | Intake | chore/frontend-docs-plan-tickets-v2 (PR #55) |
| AE-0235 | De-bloat 6 oversized guides into quick-ref + deep-dive | T2 | Intake | chore/frontend-docs-plan-tickets-v2 (PR #55) |
| AE-0236 | Fix stale doc content (API_CONTRACT, legacy-removal status) | T1 | Intake | chore/frontend-docs-plan-tickets-v2 (PR #55) |

Done vs pending: 0 done / 6 pending (all Intake).

## Stream: Agent refactoring (agent-layer restructure epic)

Backed by 5 **Accepted** ADRs (0013–0017) and the epic doc
[`docs/plans/agent-architecture-restructure-epic.md`](agent-architecture-restructure-epic.md).

| AE-# | Title | Tier | Status | Branch (PR) |
|------|-------|------|--------|-------------|
| AE-0242 | Delete dead TEMPLATE_ENFORCE prompt constant (no importer) | T1 | Intake | chore/agent-restructure-epic-tickets (no PR) |
| AE-0243 | Migrate 4 active hardcoded prompts to the registry | T2 | Intake | chore/agent-restructure-epic-tickets (no PR) |
| AE-0244 | Anti-hardcoded-prompt checker + rule-fires regression test | T1 | Intake | chore/agent-restructure-epic-tickets (no PR) |
| AE-0245 | Precondition audit: skill-to-file dependency graph | T1 | Intake | chore/agent-restructure-epic-tickets (no PR) |
| AE-0246 | Co-locate runtime skills into agent packages; load paths + CI gate | T2 | Intake | chore/agent-restructure-epic-tickets (no PR) |
| AE-0247 | Implement ADR-0013 chat-persistence resolution (no chat checkpointer) | T2 | Intake | chore/agent-restructure-epic-tickets (no PR) |
| AE-0248 | Extract shared Deep Agents harness (checkpointer/store/memory) | T3 | Intake | chore/agent-restructure-epic-tickets (no PR) |
| AE-0249 | Subagent taxonomy + URL-navigation researcher (wrap PlaywrightResearchTool) | T2 | Intake | chore/agent-restructure-epic-tickets (no PR) |
| AE-0250 | Per-agent facade packages + wired memory + skill/tool contract | T3 | Intake | chore/agent-restructure-epic-tickets (no PR) |
| AE-0251 | Runtime qa_reviewer subagent (non-blocking) + runtime kaizen channel | T2 | Intake | chore/agent-restructure-epic-tickets (no PR) |
| AE-0252 | DeepSeek tiered-model pilot on SourceSynthesisAgent | T2 | Intake | chore/agent-restructure-epic-tickets (no PR) |

Done vs pending: 0 done / 11 pending (all Intake).

## Stream: Tooling / process (dev-wave CI/eslint/commitlint/docs + kaizen)

| AE-# | Title | Tier | Status | Branch (PR) |
|------|-------|------|--------|-------------|
| AE-0220 | Serialize prod deploys with a concurrency group in deploy.yml | T1 | Review | feat/dev-wave-ae0220-0227 (PR #54) |
| AE-0221 | Document commitlint lowercase-subject convention in CLAUDE.md | T1 | Review | feat/dev-wave-ae0220-0227 (PR #54) |
| AE-0222 | Make invalid-status error self-documenting + document ticket lifecycle | T1 | Review | feat/dev-wave-ae0220-0227 (PR #54) |
| AE-0223 | Stop committing generated BOARD.md; gitignore + render on demand | T1 | Review | feat/dev-wave-ae0220-0227 (PR #54) |
| AE-0224 | no-magic-numbers + centralize API_BASE / HTTP_STATUS | T2 | Review | feat/dev-wave-ae0220-0227 (PR #54) |
| AE-0225 | Frontend data-loading pattern: React Suspense ADR + guide + QA checklist | T2 | Review | feat/dev-wave-ae0220-0227 (PR #54) |
| AE-0226 | Frontend lint: enforce early returns (no-else-return) | T1 | Review | feat/dev-wave-ae0220-0227 (PR #54) |
| AE-0227 | Fix the failing npm-audit high vuln (frontend Security gate) | T1 | Done | feat/dev-wave-ae0220-0227 (PR #54) |
| AE-0237 | Board-mutating ticket tooling: regenerate-or-noop when BOARD.md absent | T2 | Intake | chore/kaizen-018c-tooling-tickets (no PR) |
| AE-0238 | Block duplicate ticket IDs + harden next_ticket_id allocation | T2 | Intake | chore/kaizen-018c-tooling-tickets (no PR) |
| AE-0239 | gates.sh preflight: distinguish missing tool from real violation | T1 | Intake | chore/kaizen-018c-tooling-tickets (no PR) |

Done vs pending: 1 done (AE-0227) / 7 in Review (AE-0220–0226) / 3 pending Intake (AE-0237–0239).

---

## Branch stack / landing order (base → top)

| Order | Branch | Tickets | PR |
|-------|--------|---------|-----|
| 1 (base) | `feat/dev-wave-ae0220-0227` | AE-0220..0227 | **PR #54** (open, do-not-auto-merge) |
| 2 | `chore/frontend-docs-plan-tickets-v2` | AE-0228..0236 | **PR #55** (open, stacked on #54) |
| 3 | `chore/kaizen-018c-tooling-tickets` | AE-0237..0241 | no PR yet (local) |
| 4 (top) | `chore/agent-restructure-epic-tickets` | AE-0242..0252 + ADRs 0013–0017 + epic doc | no PR yet (local) |

Merge strictly base-first: #54 → #55 → (open PRs for branch 3, then 4).

## Open / untracked

- **3 client-page raw-fetch sites not yet ticketed** — the personas, rubrics, and
  workflow client pages still do raw `fetch` and are not covered by the Suspense/fetch
  tickets (AE-0228..0230). Needs a follow-up ticket.
- **AE-0247 / AE-0248 unblocked** — both were gated on **ADR-0013**, which is now
  **Accepted** (commit `437528db`). They are clear to proceed.
- **AE-0237 (board-tooling fix) should land before PR #54 merges** — it fixes the
  board-mutating ticket tooling; landing it first avoids regenerating/committing
  `BOARD.md` churn during the #54 merge.

## Quick counts

| Stream | Tickets | Done | Review | Intake |
|--------|---------|------|--------|--------|
| Frontend data-layer | 5 | 0 | 0 | 5 |
| Docs reorg | 6 | 0 | 0 | 6 |
| Agent refactoring | 11 | 0 | 0 | 11 |
| Tooling / process | 11 | 1 | 7 | 3 |
| **Total** | **33** | **1** | **7** | **25** |
