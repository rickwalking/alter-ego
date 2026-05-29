---
name: carousel-pipeline-research
description: Research phase of the editorial carousel workflow. Synthesize authoritative sources in parallel before human review. Use when the workflow enters the research phase or research revision is requested.
version: 2.0.0
---

# Research Phase

## Shared standards (read first)

- [`../_shared/critical-rules.md`](../_shared/critical-rules.md) — user sources authoritative, fact-checking, fail-loudly, search fallback
- [`../_shared/anti-patterns.md`](../_shared/anti-patterns.md) — topic drift, approve-before-generate, empty gates
- [`../_shared/content-contracts.md`](../_shared/content-contracts.md) — `ResearchSource` entity fields

## Purpose

Collect fact-checked sources that anchor the carousel to the user's actual topic. Research runs at **phase enter** via `SourceSynthesisAgent` — not on brief approval in the resume handler.

## Parallel agent dispatch

Launch 3-4 research agents IN PARALLEL targeting different source types:

| Agent | Source type | Method |
|-------|------------|--------|
| Agent 1 | Twitter/X, primary sources | Playwright MCP `browser_navigate` + `browser_snapshot`. Use https://xcancel.com/ — paste the URL after `/x/` with the post id, or visit the profile when X blocks direct scraping. |
| Agent 2 | News, blog articles | WebSearch + WebFetch across tech publications (TechCrunch, Ars Technica, The Verge, Wired, MIT Technology Review) |
| Agent 3 | Reddit, community | r/programming, r/ClaudeAI, r/LocalLLaMA, Hacker News |
| Agent 4 | Technical sources | GitHub issues, CVEs, advisories, vendor analyses |

Each agent collects URLs, titles, and extracted content. Store as `ResearchSource` entities linked to the project.

**Source priority:** User-provided `sources` are scraped first at `relevance_score=2.0`; broad web search supplements up to 10 total sources. See [`critical-rules.md`](../_shared/critical-rules.md).

## Research output

Each `ResearchSource` must include:

- `source_url`, `source_type`, `title`, `extracted_content` (max 10000 chars), `relevance_score`

Extract: quotes, statistics, key claims with attribution.

## Editorial HITL gate

**Artifacts shown at review:** `research_findings[]` with source title, URL/type, key points, confidence.

**Human actions via `POST /workflow/resume`:**

- **Approve** — advance to outline; outline generation starts on outline phase enter, not here
- **Revise** — feedback passed to `research_synthesizer` as revision instructions; optional source add/remove triggers re-synthesis on listed sources only

**Phase lifecycle:** `in_progress` → generate → `awaiting_human` → approve or revise (loop, max 5 revisions) → next phase.

**Do not:** poll legacy `/stream` at this gate; SSE `review_required` carries the interrupt payload.

## Python execution

Subagent: `research_synthesizer` → `SourceSynthesisAgent`

Langfuse metadata: `project_id`, `phase=research`, `agent_name=research_synthesizer`, `content_type=carousel`
