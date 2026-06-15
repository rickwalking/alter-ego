# Domain Modularization — Implementation Interview Record

**Date:** 2026-06-12
**Protocol:** grill-with-docs (mattpocock/skills) — sequential questions,
recommended answers, decisions captured immediately. Adapted to project
conventions: terminology lands in `docs/architecture/domain-glossary.md`
(AE-0071), decisions in ADR-0009 (AE-0072), not in a parallel CONTEXT.md.
**Interviewee:** Pedro Marins (owner, sole contributor)

## Decisions

| # | Question | Decision | Recommended? |
|---|---|---|---|
| 1 | Operating context | **Pre-production, single user** — no real users, data replaceable | Yes |
| 2 | Breaking-change appetite | **Migrate-in-place**: tables/columns/API may be renamed with data-preserving Alembic migrations; frontend updated in the same phase; LangGraph checkpoint care = finish-or-restart | Yes |
| 3 | Core aggregate name | **EditorialProject** | Yes |
| 4 | Blog model | **One BlogPost aggregate** backed by `blog_posts`, with `origin: carousel \| standalone` linked to EditorialProject; embedded carousel blog columns migrated then dropped; one `useBlogPosts()` survives | Yes |
| 5 | Persona/Quality boundary | **Two contexts** (`persona`, `quality`) | No — deviated |
| 6 | VoiceScore owner (seam from #5) | **Persona owns** VoiceScore and `PersonaAgent.enforce()`; quality consumes via persona's public contract (dependency: quality → persona) | Yes |
| 7 | Editorial Operations | **Full module now** — must own real behavior from day one (notification dispatch, board/calendar rules); read models still built from other contexts' events, not direct table joins | No — deviated |
| 8 | `stream_entry_id` after AE-0074 | **Drop the column** (Alembic migration; nothing reads it) | Alternative chosen (rec. was leave-NULL) |
| 9 | External consumers | **None** — only the in-repo Next.js frontend and in-process workers touch API/events/DB | Yes |
| 10 | Conflict policy | **409 + refresh prompt**: expected-version on mutating endpoints, machine-readable conflict body, idempotency keys on workflow commands | Yes |
| 11 | Pacing | **Nights/weekends (~5-10h/week)** — calendar ≈ 2-3x engineer-week estimate; serial ticket lanes, one at a time; small PRs; lean on CI gates | — |

Q8 included a clarifying exchange: Redis Streams vs pub/sub, why Redis
exists (push transport for SSE/workers per ADR-004), and that PostgreSQL
remains the source of truth — recorded here because it confirmed the
ADR-0009 outbox stance ("Redis is transport, not durable consumption").

## Resolved terminology (seeds AE-0071's glossary)

Format per grill-with-docs CONTEXT-FORMAT: pick one term, list rejected
synonyms under _Avoid_.

- **EditorialProject** — the aggregate owning brief, sources, workflow
  lifecycle, owner/reviewer; produces formats as outputs.
  _Avoid:_ CarouselProject (compatibility term only), ContentProject,
  Campaign.
- **BlogPost** — the single long-form publication aggregate; carries
  `origin: carousel | standalone`.
  _Avoid:_ CarouselArticle (rejected in interview — no second blog
  representation survives), blog_markdown-as-source-of-truth.
- **VoiceScore** — persona-owned voice-match measure (≥70 gate);
  quality consumes it through persona's contract.
- **persona / quality** — two bounded contexts, not one.
  _Avoid:_ persona_quality (superseded by interview decision 5).
- **editorial_operations** — full module owning notifications and
  board/calendar behavior; its views are event-built read models.
- **Conflict response** — HTTP 409 with machine-readable body on stale
  expected-version; "refresh prompt" is the canonical UX term.

## Consequences applied (2026-06-12)

1. **Plan** (`domain-modularization.options.md`): "Interview Decisions"
   amendment — migrate-in-place variant of the scaled-down track;
   compatibility scaffolding (legacy ACL, sole-writer-forever, frozen
   schemas) reduced to per-migration-window discipline; field-ownership
   map repurposed as the migration map; contexts table updated (persona,
   quality, editorial_operations as module); calendar reforecast at
   5-10h/week.
2. **AE-0071**: decisions 3-7 pre-seeded; glossary transcribes.
3. **AE-0072**: operating-context statement now answerable from this
   record (plus AE-0075's checkpoint count); track = scaled-down +
   migrate-in-place.
4. **AE-0073**: 409/idempotency contract upgraded from draft to decided.
5. **AE-0074**: drop `stream_entry_id` (migration added to scope).
6. **AE-0075**: escalation downgraded — a CLASS-PATH-DEPENDENT verdict no
   longer blocks Phase 2.5; policy is finish-or-restart in-flight
   workflows (owner's consent = self).
7. **AE-0076**: protects the in-repo frontend contract only (no external
   consumers exist).

## Open items deliberately NOT decided here

- Exact new table/column names (AE-0071 glossary + per-phase migrations).
- Outbox implementation details (Phase 6, per ADR-0009 section).
- Whether the round-3 cold-review verdict needs a delta review for the
  migrate-in-place amendment — recommended before Phase 1 starts, since
  the amendment is material (it mostly REMOVES risk machinery, but a
  blind check that nothing protective was over-removed is cheap).
