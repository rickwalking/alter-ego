# ADR-001: Adopt MADR for Architecture Decision Records

## Status

Accepted

## Context

Alter-Ego is pivoting from an autonomous AI content factory to a professional human-in-the-loop platform. This transformation involves significant architectural changes (workflow engine, persona system, quality rubrics, blog posts with editorial states). Without a decision log, future developers and stakeholders will struggle to understand why certain technologies and patterns were chosen.

## Decision

We will use **MADR 4.x (Markdown Architectural Decision Records)** as our ADR format, stored in `docs/decisions/`.

## Consequences

**Good:**
- Low friction — Markdown is native to our toolchain
- Version control friendly — lives in Git alongside code
- Structured but lightweight — MADR balances detail with readability
- Industry standard — widely adopted, tooling exists (adr-tools)

**Bad:**
- Requires discipline to maintain alongside feature work
- Can become stale if not reviewed regularly
- No built-in enforcement — relies on team culture

## Alternatives Considered

| Format | Why Rejected |
|--------|-------------|
| Nygard | Too minimal for our multi-phase pivot; lacks decision drivers section |
| Tyree & Akerman | Too heavyweight; compliance overhead not needed |
| Wiki/Confluence | Outside version control; drifts from code reality |
| Inline code comments | Doesn't capture context, trade-offs, or rejected alternatives |

## Related Decisions

- ADR-002: Use LangGraph for Workflow Engine
- ADR-003: Implement Persona-Driven AI Content Generation
- ADR-004: Adopt Event-Driven Architecture for Content Workflows

## Tags

#process #documentation #architecture
