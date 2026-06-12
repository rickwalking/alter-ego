# QA Research Pack

## Why

The 5 QA subagents would otherwise each re-read the codebase — ~5 redundant
exploration passes, and exploration is the dominant token cost (Anthropic:
token usage explains ~80% of outcome variance; multi-agent ≈ 15× a chat). One
shared pass, written once and reused, removes ~4 of those passes. The pack also
*improves* review quality, not just cost: giving every dimension full
architectural context measurably raises review F-score (DeputyDev, arXiv
2508.09676).

## How it is built

1. **Run a dedicated read-only explorer subagent** over the change scope (the
   diff / changed files). Its model is **selectable** via `config.yaml`
   `research_pack.model` — default a cheap/fast model, overridable to any
   provider (NOT locked to Anthropic). Use the `Explore` agent type so it
   cannot edit.
2. The explorer writes the pack to `.agent/reports/AE-####.qa-research.md`
   (single ticket) or `.agent/reports/<wave-id>.qa-research.md` (wave).
3. The pack is read-only input to all 5 reviewers — never edited by them.

## Pack template

```
# QA Research Pack — <scope> @ <commit-sha>
Generated: <ts> | Diff range: <base>..<head> | Regenerate-if: diff changes

## 0. Metadata & Freshness        [ALL]
    commit SHA, branch, files-in-diff, base ref
## 1. Change Summary              [ALL]
    what the change does in 5 bullets; intent vs implementation
## 2. File Inventory & Map        [ALL]
    changed files + role of each; new / modified / deleted; entry points
## 3. Architecture & Data Flow    [security, code-quality]
    component map, request/data flow for touched paths, trust boundaries,
    external I/O (network, DB, fs, subprocess), auth/authz touchpoints
## 4. Conventions in Effect       [code-quality, AC]
    CLAUDE.md/AGENTS.md rules that apply: constants policy, type strictness,
    400-line / 3-arg limits, naming, lint/type config
## 5. Dependency Graph & Callers  [orphan, code-quality]
    who-calls-what for changed symbols; public API surface; imports added;
    newly-added-but-uncalled symbols (orphan candidates)
## 6. Test Landscape              [mutation, AC]
    existing tests covering touched code, coverage gaps, .feature files,
    fixtures/mocks available, how to run the suite
## 7. Risk Hot Spots              [ALL — flagged per dimension]
    per item: location, why risky, [tag: security|quality|tests|orphan|AC]
## 8. Acceptance Criteria Mapping [AC]
    each AC → file(s)/symbol(s) that should satisfy it; gaps
## 9. Glossary / Domain Terms     [ALL]
## 10. UNKNOWNS / NOT-VERIFIED    [ALL — anti-blind-spot]
    what the explorer could NOT confirm; reviewers MUST verify these
    independently rather than trusting the pack
```

## Role → section routing

Inject the **whole pack as a shared (cacheable) prefix** to each subagent, plus
a short brief naming the sections that matter to it. Focuses each reviewer's
reasoning without a second exploration.

| Subagent | Reads sections |
|----------|----------------|
| 1 Security | §0, §1, §2, §3, §7, §10 |
| 2 Code Quality | §0, §1, §2, §3, §4, §5, §7, §10 |
| 3 Mutation Testing | §0, §1, §2, §6, §10 |
| 4 Acceptance Criteria | §0, §1, §6, §8, §10 |
| 5 Orphan/Unfinished | §0, §1, §2, §5, §10 |

## Independence mandate (defeats the shared blind spot)

A single exploration pass can bias every reviewer (path dependency). Therefore:

- Every subagent **must re-verify §10 UNKNOWNS** in its dimension.
- Before raising **any** finding, the subagent **must confirm the underlying
  fact against live code** — it may not fail a check on a pack claim alone.
- The pack is a map, not a verdict. Anthropic deliberately preserves
  per-subagent independent verification to reduce path dependency; so do we.

## Staleness guard

The pack is a point-in-time snapshot stamped with commit SHA + diff range. If
the diff moves (e.g. a fix round changes files), **regenerate the pack** (or
just the affected sections) before re-running QA. External QA prompts must cite
the pack's commit SHA so a stale pack is detectable.
