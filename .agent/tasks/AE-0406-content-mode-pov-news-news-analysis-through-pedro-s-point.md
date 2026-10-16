# AE-0406 — Content mode `pov_news` (news analysis through Pedro's point of view) + scout quotes

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: Cross-cutting
Owner: Claude (owner request)
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0406-pov-news-mode
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

The GrokBot scout can propose `mode: "pov_news"` topics: AI news told through Pedro's point of
view (facts first, why it matters to a software developer, then his first-person read), with up
to three **verified quotes** from posts it already sent through `POST /x-signals`. The backend
drafts every slide, the voice and the caption; a quote reaches a slide only verbatim.

## Problem

Radar IA (`news_analysis`) is capped at one post a week and recaps do not grow the account;
plain POV (`pov`) argues an opinion without telling the reader what happened. The scout has the
exact words of the posts it read, but the contract had no way to pass them, and a model that
paraphrases or invents a quote is a reputational risk. Spec: GrokBot "POV News Mode Spec (v2)",
2026-10-16 (sections 1-6 and 9 in scope; section 7 assets/avatars/screenshots is phase 2;
section 8 is scout behaviour).

## Scope

- **Intake** (`POST /api/autopilot/topics`): `mode` accepts `pov_news`; it requires
  `thesis_draft` (`thesis_missing`) and ignores `pov_format`. New optional `quotes` (0-3) with the
  spec §4 rules and reason codes `quote_invalid`, `quote_source_invalid`,
  `quote_handle_mismatch`, `quote_not_in_post`, `quote_too_long` (plus `url_in_text` for a URL in
  a quote text). Quote problems reject one topic, not the batch; unknown keys stay a 422.
  Every rejection gains `index` (always) and `field` (when one field caused it).
- **Excerpt normaliser** in the autopilot domain (NFC, curly → straight quotes, whitespace runs
  → one space, trim; case-sensitive substring; 600-character stored cut).
- **Caps:** `pov_news` counts toward the daily cap, not the weekly Radar IA cap.
- **Storage:** `topic_candidates.quotes`, `carousel_projects.pov_quotes` / `pov_sources`
  (Alembic `c4d5e6f7a8b9`, single head).
- **Pipeline:** `pov_news` runs the POV pipeline end to end (thesis step, `pov_hook_v1`, slide-1
  photo, validators, persona voice gate) with a new prompt family `carousel_pov_news/v1`
  (outline, hook, content, caption + README).
- **Quotes on slides:** the content model may pick a quote by id on a point/twist slide; code
  places it verbatim (≤2 per deck, `text_pt` PT, `text_en` EN), renders it with
  `insight_quote` + an attribution row (initial circle, name, `@handle · X`, never a URL), and the
  autopilot content gate re-checks every card.
- **Caption footer** `Fontes: @handle, domain.com` appended by code.
- **Telegram + frontend:** the thesis prompt names "Ponto de Vista: Notícia"; frontend types,
  wizard option and i18n gain `pov_news` ("Ponto de Vista: Notícia" / "POV: News").
- ADR-0023, architecture doc §5.7.

## Non-Goals

- Spec §7 (phase 2): `POST /api/autopilot/assets`, `avatar_asset_id`, screenshot slides.
- Scout behaviour (spec §8) and the scout routine pack.
- A wizard input for quotes (quotes come only from the scout).
- Changing `carousel_pov/v1` or any existing prompt file.

## Acceptance Criteria

- [x] AC1 — `mode` accepts `pov_news`; absent / `news_analysis` / `pov` behave as before (regression tests).
- [x] AC2 — `pov_news` without `thesis_draft` is rejected `thesis_missing` (`field: thesis_draft`); `pov_format` is ignored.
- [x] AC3 — `quotes` (0-3) are validated per spec §4 with the five new reason codes; each problem rejects only its topic, with `index` and `field` (e.g. `quotes[1].excerpt`).
- [x] AC4 — the excerpt normaliser lives in the domain with its own tests (curly quotes, CRLF, emoji, 600-character cut).
- [x] AC5 — every rejection has `index`; `field` is present only when one field caused it; unknown keys remain a 422; existing clients keep working.
- [x] AC6 — `pov_news` counts toward the daily cap and not the weekly Radar IA cap.
- [x] AC7 — validated quotes are stored on the topic and carried into the run spec and the carousel project (`pov_quotes`, `pov_sources`); single Alembic head.
- [x] AC8 — `pov_news` takes every POV branch (thesis step, `pov_hook_v1`, slide-1 photo, role layouts, voice gate); branch list recorded below.
- [x] AC9 — outline, hook, content and caption use the new `carousel_pov_news/v1` prompts (README; no existing prompt edited; no prompt text in `.py`).
- [x] AC10 — at most 2 quote cards, verbatim (`text_pt` PT / `text_en` EN), on point/twist slides only; a model-written insight never reaches a slide; the content gate blocks a non-verbatim card.
- [x] AC11 — the quote card renders an initial circle, the name and `@handle · X`, never a URL (preview and export CSS).
- [x] AC12 — the `pov_news` caption ends with the code-built `Fontes:` footer (X → `@handle`, others → domain, deduped, `sources` order).
- [x] AC13 — Telegram thesis prompt and the frontend (types, wizard, i18n) know `pov_news`.

## Gherkin Scenarios

Full set: `backend/tests/features/autopilot_pov_news_ae0406.feature`.

```gherkin
Feature: Content mode "pov_news" and scout-verified quotes (AE-0406)

  Scenario: A quote problem rejects only that topic
    Given a batch with a valid topic and a pov_news topic whose excerpt is not in the post
    When the scout posts it
    Then the valid topic is accepted
    And the pov_news topic is rejected with "quote_not_in_post" and field "quotes[0].excerpt"

  Scenario: pov_news counts toward the daily cap only
    Given this week's Radar IA run was already created
    When a pov_news topic is posted
    Then it is queued

  Scenario: A quote is placed verbatim by id, at most twice
    Given the content model returns quote_id "q1" on a point, the twist and a third point
    When the drafts are finalized
    Then two slides carry the card with text_pt and the EN card is text_en

  Scenario: The caption footer is written by code
    Given a pov_news project with an X source and a news site source
    When the caption is generated
    Then it ends with "Fontes: @kanishksj01, anthropic.com"
```

## Delta

### ADDED

- `domain/content_mode.py` (`is_pov_family`, `is_pov_news`, `pov_prompt_domain`),
  `domain/models/news_quote.py`, `domain/news_quote_cards.py`, `domain/source_footer.py`,
  `domain/constants/news_quotes.py`.
- `modules/autopilot/domain/{quote_text,quotes,intake_rules}.py`,
  `modules/autopilot/{quote_constants,intake_constants}.py`,
  `modules/autopilot/infrastructure/quote_gate.py`.
- `agents/pov_quote_context.py`, `agents/prompts/carousel_pov_news/v1/*`.
- `application/services/carousel_template/strategies/news_quote.py`.
- Alembic `c4d5e6f7a8b9_pov_news_quotes.py`; ADR-0023.

### MODIFIED

- Intake schema/mapping/domain/service/store, run spec, thesis, POV choice, gate snapshot,
  editorial driver, POV project fields, x-signal text storage (line breaks → spaces).
- Content-mode brief, outline/content/caption prompt routing, generators, distribution pack,
  role layouts, `insight_quote`, POV CSS + export CSS, carousel create schema, project policy,
  editorial ACL `is_pov`, carousel ORM content-mode columns.
- Frontend `CONTENT_MODES`, carousel schemas, wizard mode section, sidebar, i18n.

### REMOVED

- None.

## Affected Areas

- Backend: autopilot intake, run, gate; carousel pipeline (prompts, drafts, distribution, render).
- Frontend: content-mode constants, schemas, wizard labels.
- Database: 3 nullable JSON columns (`c4d5e6f7a8b9`).
- API: `POST /api/autopilot/topics` (additive: `pov_news`, `quotes`, `index`, `field`);
  carousel create accepts `content_mode: pov_news`.
- Tests: unit + integration (see Test Evidence), feature file.
- Docs: ADR-0023, `docs/architecture/grokbot-autopilot.md` §5.7.
- Prompts/LLM: new `carousel_pov_news/v1`.
- Observability: none new (same Langfuse paths).
- Deployment: prod has no `alembic_version` and migrate-on-deploy is disabled in `deploy.yml` (AE-0207), so the three columns (`topic_candidates.quotes` jsonb, `carousel_projects.pov_quotes` json, `carousel_projects.pov_sources` json) were applied manually on prod before merge (2026-10-16, orchestrator). The revision is idempotent.

## Dependencies

- Blocks: GrokBot scout routine v4 (sending `pov_news` + quotes).
- Blocked by: none.
- Related: AE-0371 (POV epic), AE-0377 (thesis gate), AE-0360 (x-signals), ADR-0020, ADR-0021.

## Implementation Plan

1. ADR-0023, ticket, feature file.
2. Domain: mode family helpers, `NewsQuote`, normaliser, quote rules, intake rules with `field`.
3. Intake API/service/store + migration; run spec → project fields.
4. Pipeline: brief/prompt domain, new prompts, quote placement, EN cards, footer, render, gate.
5. Telegram label, frontend, docs; gates; PR; CI green.

## QA Checklist

- [x] Security reviewed (quote text is escaped in HTML; no URL rendered; prompt data sanitized)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-16

Ticket created; ADR-0023 written; backend, prompts, frontend and tests implemented.

## Files Touched

PR #124 (`feat/ae-0406-pov-news-mode`). Main groups:
- **Autopilot:** `modules/autopilot/{api,application,domain,infrastructure}`.
- **New domain modules:** `domain/{content_mode,news_quote_cards,source_footer}.py`, `domain/models/news_quote.py`, `domain/constants/news_quotes.py`.
- **Carousel pipeline:** content-mode brief, generators, distribution pack, prompts, role layouts, `insight_quote`/`news_quote` strategies, POV CSS and export CSS.
- **Agents:** `agents/{content_draft_agent,pov_outline_mixin,pov_quote_context}.py` and the `carousel_pov_news/v1` prompts.
- **Migration:** `alembic/versions/c4d5e6f7a8b9_pov_news_quotes.py`.
- **Frontend:** constants, schemas, the create wizard, i18n.
- **Docs:** ADR-0023, ADR-0021, root `CLAUDE.md`, `docs/architecture/grokbot-autopilot.md` §5.7.

## Test Evidence

- **CI:** all 34 checks green at `806f0eb9`, including backend test, diff-cover, migrations (fresh DB) and mutation at 79.43%. The full GATES_JSON is in `.agent/reports/AE-0406.dev-summary.md`.
- **Locally:** static gates PASS; targeted backend suites green; frontend `create/` vitest green.

## QA Report

[`.agent/reports/AE-0406.qa.md`](../reports/AE-0406.qa.md). Mode `self-fallback`: opencode, codex and cursor were all unavailable. QA ran as three independent review agents (security/integrity, code quality/mutation, AC/Gherkin). Each returned WARN with no blockers, and every actionable finding is fixed.

## Content-mode branch list (AE-0406)

Every place that branched on `content_mode == pov` (or "is this POV?") and what `pov_news` does:

| Branch | `pov_news` | Why |
|---|---|---|
| `autopilot/api/schemas.py` `mode` pattern (`SCOUT_MODE_PATTERN`) | accepted | new mode |
| `autopilot/domain/intake_rules.py` thesis rule | takes it (`thesis_missing`) | POV family |
| `autopilot/domain/intake.py` `is_news` (weekly cap) | **not** news | daily cap only (spec §6) |
| `autopilot/infrastructure/intake_store.py` `news_runs_created_between` | not counted | unchanged query (NULL / `news_analysis`) |
| `autopilot/domain/pov_choice.py` `pov_choice_for` | keeps slide count, drops format | spec §3 |
| `autopilot/domain/thesis.py` `is_pov` / `needs_thesis` | takes it | thesis step |
| `autopilot/domain/thesis.py` `thesis_prompt_text` | own label "Ponto de Vista: Notícia" | Telegram shows the mode |
| `autopilot/application/run_spec.py` image style / thesis / format / count / photo / refusal | takes it | POV family |
| `autopilot/infrastructure/pov_project.py` policy version + POV fields | takes it, + quotes/sources | POV family |
| `autopilot/domain/pov_schedule.py` `is_pov_run` (Tue/Thu prior) | takes it (run has `pov_thesis`) | same publish rhythm as POV |
| `editorial/infrastructure/carousel_automation.py` `is_pov` (voice gate) | takes it | voice must be scored |
| `api/schemas/carousel_content_mode.py` create rules / slide range / format | takes it; format forced to default | POV family |
| `application/services/carousel/project_policy.py` create-time contract | `pov_hook_v1` | POV family |
| `content_mode_brief.py` `is_pov` → `outline_by_mode`, `slide_policy_context` | takes it | POV outline + per-role drafting |
| `pov_outline_mixin.py`, `content_draft_agent.py` prompt domain | `carousel_pov_news` | voice differs |
| `carousel_template/prompts.py` caption | `carousel_pov_news/v1/caption` | voice differs |
| `carousel_template/role_layouts.py` role → layout | takes it | POV layouts |
| `role_layouts.quote_card_strategy` / `insight_quote` news card | **only** `pov_news` | quotes are `pov_news`-only |
| `editorial_distribution_pack.py` EN cards + `Fontes:` footer | **only** `pov_news` | spec §4-§5 |
| `editorial_workflow_generators.py` quote placement | **only** `pov_news` | spec §4 |
| `autopilot/infrastructure/quote_gate.py` content-gate re-check | **only** `pov_news` | spec §4 |
| Branches on `policy.has_roles` (hook API, export, outline sizing) | takes it | contract is `pov_hook_v1` |

## Decision Log

- 2026-10-16: **`pov_news` is stored as its own `content_mode`** (not a `pov` sub-format). A
  POV-family helper (`domain/content_mode.py`) answers "is this a POV deck?"; voice branches use
  the exact mode. `content_mode` is a plain `String(20)`, so no enum migration.
- 2026-10-16: **`pov_format` is ignored for `pov_news`**: the topic stores none and the project
  stores the default `opiniao`, which only picks the point-slide layout; the news narrative lives
  in the `carousel_pov_news/v1` outline. The wizard still shows the format cards (they pick the
  layout); the API stores the default.
- 2026-10-16: **New prompt family `carousel_pov_news/v1` with all four prompts** (outline, hook,
  content, caption): each one's voice differs. Selected by domain (`pov_prompt_domain`), same
  names and version as `carousel_pov/v1`, which is untouched.
- 2026-10-16: **The model never writes a quote.** On point/twist slides it may return `quote_id`;
  code places the card from the stored quote (≤2, each quote once, first by slide order) and drops
  any model-written `insight` on a `pov_news` deck. EN cards are added to the EN translations in
  the distribution step, so PT/EN shapes match.
- 2026-10-16: **Verbatim check runs at the autopilot content gate** (`quote_gate.py` →
  `GateSnapshot.quality_violations`, codes `quote_not_verbatim` / `too_many_quote_cards`) instead
  of inside `validate_localized_slides`, which has no access to the project's quotes and is
  shared by ~10 callers (and AE-0405 is changing `phase_artifact_runner.py`). Placement is
  verbatim by construction; the gate is the backstop before anything is auto-approved; an owner
  edit in the web UI is the owner's call.
- 2026-10-16: **Quote card render:** `insight_quote` renders a card with `handle` on the POV
  statement shell (heading, body, card) with the attribution row; other insights keep the
  lower-third layout. `quote_card_strategy` wins over the role layout so a twist card is never
  dropped. Quote text is HTML-escaped and has no inline markup.
- 2026-10-16: **Quote rules:** handle compared case-insensitively (X handles are); the URL must
  already be canonical (`https://x.com/<handle>/status/<id>`, so `twitter.com` is
  `quote_source_invalid`); a URL inside a quote text is `url_in_text`; quotes on a non-`pov_news`
  topic are `quote_invalid` (`field: quotes`); a 4th quote is `quote_invalid` (`field: quotes`);
  schema caps (10 quotes, 2000 chars per field) are abuse limits only, so domain rules return reason
  codes instead of a 422. The first failing rule wins (order: id, name, lang, empty texts, URLs,
  source, handle, excerpt, word limits).
- 2026-10-16: **x-signals now stores line breaks as spaces** (they were dropped as control
  characters, gluing words). Needed so an excerpt can span a line break; only affects new
  observations.
- 2026-10-16: **`field` for existing reasons too** (`empty_text`, `url_in_text`, `sources[i]`,
  `thesis_draft`, carousel-default fields); caps and duplicates have no `field`. The route drops
  `field: null` (`response_model_exclude_none`).
- 2026-10-16: **Caption footer** is appended after the model caption, idempotently; X hosts
  (`x.com`, `twitter.com`, `www.`/`mobile.` dropped) show `@handle`, others the bare domain.
- 2026-10-16: **Telegram:** only the thesis prompt shows the mode today, so only it changes
  ("🧭 Ponto de Vista: Notícia proposto"); the review message does not show a mode and is unchanged.
- 2026-10-16 (PR #124 review): **prod columns applied manually before merge (2026-10-16)**;
  migrate-on-deploy is disabled (AE-0207), so the ticket no longer claims "applied on deploy".
- 2026-10-16 (PR #124 review): **a missing or blank quote field is `quote_invalid`** with
  `field: quotes[i].<name>` (first blank in spec order) instead of a batch 422; the schema
  makes every quote field optional and keeps `extra="forbid"`.
- 2026-10-16 (PR #124 review): **X status URLs compare case-insensitively on the handle**
  (`status_key`: lowercase host + handle, status id kept) for the sources check, the
  stored-post lookup (`lower(url)` in SQL) and the excerpt lookup, matching the handle check.
- 2026-10-16 (PR #124 review): **footer dedup is case-insensitive** (first spelling kept);
  **the wizard hides the POV format picker for `pov_news`** and sends no `pov_format`.
- 2026-10-16 (QA): **a single-slide retry drops its quote card** (`_without_quote_card`): the
  2-card cap is per deck and the retry cannot see the other slides. The excerpt is cleaned like
  the stored text (whitespace runs → space, then controls dropped) so a `\x00` never reaches JSONB.
- 2026-10-16 (QA, accepted): the `pov_hook_v1` warning `first_person_missing` (needs 3
  first-person slides) will often fire on `pov_news`, whose voice keeps "eu" to the pov/twist
  slides. It is a **warning** (never blocks the gate); kept as is rather than adding a
  mode-specific exemption to the shared contract. Revisit with a `pov_news` contract if noisy.
- 2026-10-16 (QA, accepted): the case-insensitive x-signal lookup (`lower(url) IN`) cannot use
  the primary-key index; `autopilot_x_signals` holds a few hours of posts, so the scan is small.
- 2026-10-16 (QA, accepted): an unknown `pov_format` value is still a 422 on any topic (as for
  `news_analysis` today); the owner refine tool may rewrite a caption without the footer
  (owner's choice).
- 2026-10-16: **Migration `c4d5e6f7a8b9` chains on `a0e4f0a4b4c4`** (AE-0404). A parallel ticket
  adding a revision on that head needs a `down_revision` rebase at merge.

## Blockers

None.

## Final Summary

Pending.
