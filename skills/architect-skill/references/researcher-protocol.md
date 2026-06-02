# Research Protocol

## Source priority

1. `docs/decisions/`, `CLAUDE.md`, `docs/architecture/`
2. Official vendor docs / Context7
3. GitHub (org + reputable OSS)
4. Engineering articles
5. Reddit / gist — weak signal; label confidence LOW

## Parallel threads (one message, N subagents)

- `official-docs` — vendor + Context7
- `github` — implementations, issues
- `articles` — web search, blogs
- `community` — Reddit/HN summaries
- `alter-ego` — repo patterns, ADRs

## Rounds

1. Decompose question into threads
2. Parallel gather (read-only)
3. Synthesize option matrix (pros/cons/risk/effort/ADR fit)
4. Human checkpoint — pick or request more ideas
5. Update arch-plan; max **3** rounds default

## Outputs

- `.agent/reports/AE-####.research.md`
- `.agent/reports/AE-####.options.md` (recommended option marked)
