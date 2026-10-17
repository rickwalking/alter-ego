# Instagram growth: "Ponto de Vista" mode, Radar IA fixes and autopilot wiring

Status: proposed (AE-0371 epic) · Date: 2026-10-15 · ADR: [ADR-0021](../decisions/0021-content-mode-pov.md)

Source: the owner's Instagram growth plan (section 16: 16.3 POV mode spec, 16.4 Radar IA
adjustments, 16.5 R0–R8 roadmap). Sections 4–8 and 10–13 of that plan give the editorial
rationale (formats, hook formulas, slide structure, cadence, KPIs) and feed the prompt and
rubric content below.

**Core rule for the whole epic:** the model may sharpen Pedro's thesis, but it never invents
their opinion, experiences, test results or numbers. Every POV prompt states it, the rubric
checks it where it can, and no fixture or example invents a claim on Pedro's behalf.

## 1. Verified current state (2026-10-15, `main` @ b7b264c)

The plan was written against an older read of `main`. Each claim was re-checked:

| Plan claim (16.1 / 16.4) | Current code | Verdict |
|---|---|---|
| `SWIPE_TEXT_PT = "Swipe →"` on PT slides | `domain/constants/carousel.py:74` and `blog_language.py:6-7` both still English | still true, fix in R1 |
| Caption prompt is `carousel/v2/caption_prompt.yaml`, 12–18 hashtags, double CTA | `carousel_template/prompts.py:55` hard-codes `version="v2"`; only caller is `editorial_distribution_generation.py:75` (autopilot uses the same path) | still true. **`carousel/v3/` already exists** (outline/content), so the new caption goes in a new `v7/` folder, not `v3/` |
| CTA copy fixed "Siga para mais conteúdo como esse" | inline literals in `strategies/cta.py:55,57` **and** `carousel_template/slides.py:157,159` | still true (two places) |
| Counter renders `0{n} / {total:02d}` | five sites: `cta.py:62`, `lower_third_shell.py:46`, `slides.py:66,93,120,163`; `html_template.py:47-61` dots counter is unpadded and fine | still true, wider than the plan said |
| UI default Comic Neon vs backend `neo_anime` | `frontend/src/constants/create.ts` (`openai__comic_neon` first) vs `IMAGE_STYLE_DEFAULT = neo_anime` and autopilot `DEFAULT_IMAGE_STYLE = neo_anime` | still true |
| Fixed 7 slides, `MAX_SLIDES = 7` | `MAX_SLIDES = 7` lives in `application/services/carousel/types.py:25`; autopilot has its own `MAX_SLIDES = 10` (`modules/autopilot/constants.py`) used by the gate; `outline_normalize.py` forces the 7 canonical slide types by position and **drops every other outline key** | still true; normalizer is the real constraint |
| Policy `slide_count` validated against the outline | loader only checks `len(slide_sequence) == slide_count`; `VIOLATION_SLIDE_COUNT_INVALID` is never emitted; outline is trimmed by slicing | the outline-length check does not exist yet |
| Template choice never reaches the API | wizard sends `strategy`; schema accepts it; `crud.py` drops it | still true (fixed in R2 because POV formats pick a layout) |
| Persona page empty → "not scored" | wizard never sends `persona_id`; project `persona_id` never set at create | still true; R2 wires the select |
| Autopilot publishes right after Approve | AE-0370 (in flight on `fix/ae-0370-scheduled-publish`, not on `main`) adds Telegram scheduling, `scheduled_at`, `AUTOPILOT_DEFAULT_PUBLISH=now|next_slot` | **stale**: R6 is owned by AE-0370; this epic adds only POV slot glue |
| Autopilot Story + music | AE-0369 shipped: Story after each post, music suggestion in the notice | **stale**: already live in code |
| Quota / casing problems | AE-0368 (`fields=quota_usage,config`) and AE-0366/0367 (sentence case, proper nouns) shipped | **stale**: done |
| "Failed to load analytics" | `use-editorial-analytics.ts:22` throws on any non-OK from `GET /api/editorial-analytics`, a blog/editorial metrics route gated by the `RequireQualityChecks` feature flag (404 when off); no Instagram insights exist anywhere | root cause candidate found; R8 |
| Creator assets: "one avatar" | many assets per owner already (`carousel_creator_assets`, unique `(owner_id, sha256)`), bound one per project; **no list endpoint, no role** | partly stale; R5 adds role/pose + list |
| Images node honours `image_required` | images node uses a hard-coded `IMAGE_SLIDE_TYPES` set; the policy flag only reaches the LLM instruction text | false; R5 makes the node policy-aware |
| `playwright_export.py:300` | always loads the default (v1) policy | noted; not in scope (it only reads geometry, identical across versions) |

## 2. Approach in one paragraph

Add a **content mode** to the carousel project: `news_analysis` ("Radar IA", the default and
the meaning of every existing row, including `NULL`) or `pov` ("Ponto de Vista"). POV carries
the owner's **thesis** (required, ≤280), optional **personal proof** (≤500), a **format**
(opinião / como eu faço / erros e mitos / comparação), a **slide count** (8–10), a **CTA goal**
(follow / send / comment) and a **slide-1 photo** from the creator photo library. The mode
selects (a) the presentation contract (`pov_hook_v1` vs `hero_lower_third_v4`), (b) the prompt
family (`carousel_pov/v1` vs `carousel/v7`), and (c) the layout strategy per slide **role**.
Downstream machinery (validators, casing repair, translation, artifact build, autopilot gates)
keeps working because every POV role maps onto an existing slide type.

## 3. Key design decisions

### D1. Roles on top of existing slide types (not new slide types)

The plan names six POV slide types (`hook`, `rehook`, `pov`, `point`, `twist`, `save`, `cta`).
Every validator, copy budget, casing rule, translator, structured-extra check, artifact-health
check and layout lookup is keyed by the five existing `slide_type`s. Adding six new types would
touch all of them and risk the live Radar IA pipeline. Instead, the contract gains an optional
**`role`** per slide and each role maps to an existing type:

| Role | Slide type | Layout strategy | Artwork | Copy budget (prompt + validator) |
|---|---|---|---|---|
| `hook` | `intro` | `hook_face` | uploaded photo, no generation | heading ≤60 chars / ≤10 words; sub ≤80 |
| `rehook` | `content` | `statement` | none | heading ≤64; body ≤90 (prompt) |
| `pov` | `content` | `statement` | none | body ≤200 |
| `point` | `content` | `statement` / `numbered_list` / `feature_grid` | optional flat editorial | heading ≤64; body ≤160 |
| `twist` | `content` | `insight_quote` | none | ≤160 |
| `save` | `summary` | `save_checklist` | none | 3–5 items, ≤60 each |
| `cta` | `cta` | `cta_follow` | avatar | ≤120 |
| Radar IA v4: `news` | `summary` | (existing) | per policy | at most one |

Roles never come from the LLM. Right after an outline is generated for a project whose
contract has roles (POV, Radar IA v4), the generator stamps `role` and `slide_type` **by
position from the expanded contract**, so the outline always carries a complete role set. The
normalizer keeps `role` when every slide carries a known role; an outline with no roles (every
project stamped v1–v3) takes today's positional 7-slide path, byte-for-byte unchanged. A
length outside the contract range is trimmed to the max and reported as `slide_count_invalid`;
it never silently degrades to the legacy path (skeptical review #3).

### D2. Variable slide count in the contract

`pov_hook_v1.yaml` keeps the existing `slide_count` key (=10, the longest sequence, so the old
loader invariant still holds) and adds `slide_count_min: 8`, `slide_count_max: 10`. The four
`point` slides are marked `optional: true`; `expand_policy_for_count(policy, n)` keeps the first
`n − 6` points and renumbers. Contracts without the new keys behave exactly as before
(`min = max = slide_count`). `MAX_SLIDES` becomes 10 (Instagram's carousel limit), the legacy
positional path keeps its own `LEGACY_SLIDE_COUNT = 7`, and a new deck-level
`slide_count_invalid` check (code already declared as a blocker) fires when the outline length
is outside `[min, max]`.

`hero_lower_third_v4.yaml` (new Radar IA contract, stamped on **new** `news_analysis`
projects; v2/v3 projects keep their frozen policy, per the owner): same 7-slide spine with roles,
`image_required: false` on the summary (`news`) and closing (`verdict`) slides, and an optional
8th `twist` slide (`slide_count_min: 7`, `slide_count_max: 8`).

### D3. Persistence (one additive migration in R2, one in R7, one in R8)

All columns are nullable; no existing column changes; `NULL` means Radar IA.

- `carousel_projects`: `content_mode` varchar(20), `pov_thesis` varchar(280),
  `pov_personal_proof` varchar(500), `pov_format` varchar(30), `slide_count` integer,
  `cta_goal` varchar(20), `hook_text` varchar(120), `hook_asset_id` FK
  `carousel_creator_assets.id` ON DELETE SET NULL. (`persona_id` already exists; R2 starts
  writing it at create.)
- `carousel_creator_assets`: `role` varchar(16), `pose_tag` varchar(40).
- R7: `topic_candidates.content_mode` varchar(20), `topic_candidates.thesis_draft`
  varchar(280); `autopilot_runs.pov_thesis` varchar(280).
- R8: new table `instagram_post_insights` (one row per media id, latest snapshot).

Prod deploys run neither Alembic nor `create_all` for these columns, so the exact SQL for each
migration is recorded in `.agent/reports/AE-0371.dev-summary.md` for the orchestrator to apply
by hand; that SQL uses `ADD COLUMN IF NOT EXISTS` / `CREATE TABLE IF NOT EXISTS` so it is
safe to re-apply. **Alembic head:** AE-0370 adds `a9b0c1d2e3f4` on top of `f8a9b0c1d2e3`. This branch merged
AE-0370 and re-pointed its first (never-merged) migration `b0c1d2e3f4a5` onto `a9b0c1d2e3f4`, so
the chain is linear and `c2d3e4f5a6b7` is the single head. A migration that reached `main` is never edited (skeptical review #1).

### D4. Where the mode is read: from the project row, at generation time

The workflow input (`EditorialWorkflowStartInput`) does not carry project fields, and resumes
rebuild it from state. Rather than threading seven new fields through the LangGraph state, the
generators read a frozen `ContentModeBrief` from the project row (`project_id` is in state)
through a small port (`ContentModeBriefSource`). Manual, autopilot and resumed runs therefore
all see the same thesis. POV inputs are create-only (like topic/audience today), so they
cannot change between phases; only `hook_text` is editable, by design (the hook picker). No
`datetime.now()` or randomness enters graph logic.

### D5. Hook candidates live with the outline

`carousel_pov/v1/hook.yaml` (and `carousel/v7/hook.yaml` for Radar IA) returns 5 PT candidates,
one per formula (opinião contrária, erro + custo, "Pare de…", primeira pessoa + resultado,
lacuna de curiosidade, número específico, mito; Radar IA adds "Todo mundo falou de X. Ninguém
falou disso." and "O que o [modelo] muda pra quem programa"). Each ≤10 words, no clickbait, and
each must be paid off later in the carousel. They are stored on slide 1 of the outline
(`hook_candidates`) so the outline gate payload already carries them. The owner picks or edits
one in the outline review (`PUT /api/carousels/{id}/hook`, stored as `hook_text`, validated
≤60 chars / ≤10 words); the content phase uses `hook_text` as the slide-1 heading, else
candidate #1. The autopilot does not pick (it auto-approves the outline), so it uses
candidate #1.

### D6. Prompts (new versioned folders only)

- `carousel_pov/v1/{hook,outline,content,caption}.yaml` (+ README). Directory-discovered by
  the registry; no registry code change is needed (the plan's "register in registry.py" is
  stale).
- `carousel/v7/{hook,outline,content,caption_prompt}.yaml` (+ README) for Radar IA: angle rule
  (≤1 "what happened" slide, ≥3 "what changes for you", closing = Pedro's verdict), slide 1 =
  hook, caption with 3–5 hashtags and one CTA. v2–v6 stay frozen; the v7 outline/content are
  used only by projects stamped `hero_lower_third_v4`, so existing projects keep v3/v6.
- `ops/grokbot/grok-bot/v3/{routine.md,topics.example.json}` (v2 kept).
- The never-invent rule is written into every POV template: "if no proof is given, argue from
  reasoning, never from a fake anecdote; never invent numbers, tests, clients or results".

### D7. Rubric additions are deterministic validators

The rubric loader requires every rubric item to name rule codes with a severity, and a test
seeds one violation per code. New codes (POV contract only):

| Code | Check | Severity |
|---|---|---|
| `hook_word_limit` | slide-1 PT heading > 10 words | blocker |
| `first_person_missing` | fewer than 3 slides contain a PT first-person marker (`eu`, `meu`, `minha`, `meus`, `minhas`, `comigo`, `me`) | warning |
| `thesis_not_early` | no content word of the thesis appears in slides 1–2 | warning |
| `slide_count_invalid` | deck length outside `[min, max]` (role contracts only) | blocker (existing code) |

"At most one news slide" is structural, not a validator: roles are stamped by position and a
contract has at most one `news` slot (Radar IA v4; POV has none). A validator counting `news`
roles could never fire, so the rule lives in the contract shape and in the outline prompts.

The heuristic ones are warnings: they surface in review without blocking, so they can never
wedge the autopilot. The autopilot persona ≥70 gate (`modules/autopilot/domain/policy.py`)
applies unchanged once a persona is set.

### D8. Layout strategies and the photo library

New strategies `hook_face`, `statement`, `save_checklist`, `cta_follow` (registered in
`strategies/registry.py`, CSS in a new `css/slide_styles_pov.py`). The HTML builder picks a
strategy by `role` first (`ROLE_STRATEGY` map) and falls back to today's lookup when a slide
has no role. `cta_follow` renders the `cta_goal` copy and keeps `marinssolutions.com` small.

Creator assets gain `role` (`hook` / `cta` / `pov`) and `pose_tag`; a list endpoint
(`GET /api/carousels/creator-assets?role=hook`) and an upload `role` field. The wizard's
"Foto do slide 1" picks from that list (default: the last used). The project stores
`hook_asset_id`; the artifact build stages the photo the same way the CTA avatar is staged.
PNG/WebP alpha: the plan assumed it was already kept; it was not (the upload re-encoded to
RGB). AE-0376 now keeps it: a source with alpha is stored as RGBA WebP.

New image preset `openai__pov_editorial` (`IMAGE_STYLE_POV_EDITORIAL`). The images node asks
the project's policy which slides need artwork (`image_required`) instead of the hard-coded set,
so `pov_editorial` generates only for `point` slides (flat editorial wrap), and Radar IA v4
skips summary/closing. The autopilot images gate already compares against
`hero_images_total`, which now comes from the same policy-aware count.

### D9. Caption and CTA

POV caption: line 1 = the slide-1 hook; 2–4 first-person lines; one question inviting
disagreement; one CTA chosen by `cta_goal`; 3–5 hashtags, mostly PT; plain-text search
keywords; no "Salve + Compartilhe". Radar IA caption v7: same hashtag/CTA discipline.
`build_caption_prompt` routes by mode. CTA slide variants (constants, PT/EN):
follow "Siga @pedromarins.ai: eu traduzo IA em decisões reais.",
send "Manda pra quem precisa ouvir isso.", comment "Discorda? Me diz nos comentários.".
Radar IA's `cta_centered` switches to the follow variant (16.4 #5).

### D10. Autopilot (R7) and scheduling glue (R6)

- Scout v3 proposals carry `mode` (`news_analysis` / `pov`) and, for POV, `thesis_draft` plus a
  debate angle ("o que isso muda para devs brasileiros").
- A POV run never starts generation from an unconfirmed thesis: intake queues it in a new run
  state `awaiting_thesis`; Telegram shows the draft thesis with ✅ Confirmar / ✏️ Editar / ❌
  Descartar. Editar uses the existing ForceReply pending-reply mechanism; the confirmed text
  becomes `autopilot_runs.pov_thesis` and the project's `pov_thesis`. A thesis left
  unconfirmed for 72 h expires like an unanswered review.
- Weekly mix: at most one Radar IA (`news_analysis`) run per São Paulo ISO week. Like the
  daily cap, an extra Radar IA topic is stored but not queued and is listed with
  `weekly_news_cap_reached` (a duplicate stays a `duplicate_topic`); within one batch only the
  best-scored Radar IA topic is queued. POV is bounded only by the daily cap.
- R6 (Tue/Thu scheduling) is **owned by AE-0370**. This epic adds only the POV glue in
  `domain/pov_schedule.py`: the slot constants (Tue/Thu 12:00 America/Sao_Paulo). Since
  AE-0404 they are the POV prior of the slot recommender (`domain/recommend.py`): a run with a
  confirmed `pov_thesis` is POV, Approve schedules the best recommended slot of the next seven
  days (without insights, the next Tue/Thu 12:00 at least 15 min ahead), and the day/time
  picker stars the POV days. Radar IA's prior is AE-0370's 12:00/18:00/21:00.

### D11. Measurement (R8)

A read-only `InstagramInsightsGateway` (same Graph client/token provider as the publisher)
reads per-media insights for published posts (`ig_post_id` on `autopilot_runs` and the manual
publish ledger): `views`, `reach`, `saved`, `shares`, `follows`, `profile_visits`,
`total_interactions`. Snapshots are cached in `instagram_post_insights` (refresh when older
than 6 h, on demand). `GET /api/instagram/insights` (editor auth) returns rows + Section-13
ratios (follows per post, shares per 100 views). A metric the Graph API does not return is
shown as "n/d", never estimated. The dashboard shows an Instagram KPI card, and the existing
analytics card stops failing the page when the editorial-analytics flag is off (it renders an
explicit "disabled" state instead of "Failed to load analytics").

## 4. API contract changes

- `POST /api/carousels` adds optional `content_mode`, `pov_thesis`, `pov_personal_proof`,
  `pov_format`, `slide_count`, `cta_goal`, `persona_id`, `hook_asset_id`; `strategy` is now
  persisted as `slide_layout_strategy`. Validation: `pov` requires a non-blank thesis, a known
  format and `slide_count ∈ {8,9,10}` (default 9); POV-only fields are rejected (422) on
  `news_analysis`.
- `CarouselProjectResponse` adds the same fields + `hook_text`.
- `PUT /api/carousels/{id}/hook` `{hook_text}` (owner/editor, POV + Radar v4 projects).
- `GET /api/carousels/creator-assets?role=` (owner-scoped list); upload accepts `role`,
  `pose_tag`.
- `GET /api/instagram/insights`.

## 5. Frontend

Wizard: a "Modo" toggle (Radar IA / Ponto de Vista) drives the rest; POV shows tese, prova,
formato, nº de slides, foto do slide 1, objetivo do CTA; both modes show persona (prefilled
with the persona named "Pedro" if it exists, else the first). Templates list shows the four POV
formats only in POV. Outline review shows the hook candidates with pick/edit. Dashboard gains
the Instagram KPI card. Every new string is in `pt.json` and `en.json`; every new component has
a test.

## 6. Ticket breakdown (roadmap order)

| Ticket | Roadmap | Scope |
|---|---|---|
| AE-0371 | epic | coordination, owner actions (R0), dev summary, migration SQL |
| AE-0372 | R1 | "Deslize →", caption v7, CTA follow copy, counter `{n:02d}`, image default alignment (`flat_editorial` UI + backend + autopilot), outline SKILL examples, export-and-caption doc |
| AE-0373 | R2 | project columns + migration, schema/route, persona at create, strategy persisted, wizard mode toggle + POV fields, i18n |
| AE-0374 | R3 | `pov_hook_v1.yaml`, `hero_lower_third_v4.yaml`, loader ranges + roles, `expand_policy_for_count`, `MAX_SLIDES` 10, role-aware normalizer, outline-length check, autopilot gate range |
| AE-0375 | R4 | `carousel_pov/v1/*`, hook candidate step, `PUT …/hook`, POV routing in outline/content/caption, new rubric validators, outline review hook picker |
| AE-0376 | R5 | four strategies + CSS, role-based strategy selection, photo roles + list + wizard picker, `pov_editorial` preset, policy-aware images node, Radar IA `carousel/v7` outline/content + v4 stamping |
| AE-0377 | R7 (+R6 glue) | scout v3, intake `mode`/`thesis_draft`, `awaiting_thesis` + Telegram confirm/edit/discard, weekly news cap, POV slots wired into AE-0370's publish choice |
| AE-0378 | R8 | insights gateway + table + route, dashboard KPI card, analytics flag-off state |

R0 (owner actions, no code) and R6 (AE-0370) are not tickets of this epic.

## 7. Testing

- Gherkin first per behaviour ticket: `backend/tests/features/` (`radar_ia_quick_fixes`,
  `carousel_content_mode`, `carousel_variable_slide_count`, `carousel_pov_prompts`,
  `carousel_pov_layouts`, `autopilot_pov_thesis`, `instagram_insights`) and
  `frontend/tests/features/` for the wizard/outline/dashboard.
- Rule-fires tests for every new validator code (seeded violation → code emitted).
- Prompt render tests (variables present; never-invent instruction present; no Python-side
  prompt text — `inline-prompts` gate).
- Migration tests: upgrade/downgrade on SQLite, single head.
- Autopilot: thesis state machine transitions, Telegram callbacks ≤64 bytes, owner allowlist,
  idempotent confirm, weekly cap boundaries (Sunday→Monday São Paulo).

## 8. Rollout and rollback

- Merge order: AE-0370 → this epic (re-chain migration). Apply the migration SQL by hand
  **before** the deploy (columns are nullable, so old code ignores them; new code needs them).
- Feature exposure: POV appears only when chosen in the wizard or proposed by scout v3;
  scout v2 keeps working (no `mode` → `news_analysis`).
- Rollback: revert the merge; the nullable columns and new tables can stay. Old code does not
  know POV: it would render a POV project as a 7-slide Radar IA deck. POV projects are private
  until approved, so nothing broken is published; after re-deploying, regenerate the POV
  projects created in the window. No data is lost (skeptical review #2).

## 9. Risks

| Risk | Mitigation |
|---|---|
| Normalizer change alters Radar IA outlines | role path only when every slide has a known role; legacy tests pinned |
| `MAX_SLIDES` 7→10 widens slicing elsewhere | slicing now happens after normalization, which already bounded the deck |
| LLM ignores the never-invent rule | rule in every POV prompt; `personal_proof` is the only source of anecdotes; owner reviews every carousel before publish |
| AE-0370 conflicts (owner actions, state machine, migration head) | new behaviour in new files; small hook points; re-chain on merge |
| Graph insights metric names change per API version | metric list in constants; unknown/unsupported metric → "n/d", logged |

## 10. As built (2026-10-15)

Differences from the plan above, and facts found while building:

- **Hero images on Radar IA v4.** Autopilot projects are stamped `hero_lower_third_v4`, so only
  the hook and impact slides get artwork. A 7-slide deck now has 4 hero images (slides 1, 3,
  4, 5), not 6; the autopilot image gate counts the same policy-aware total.
- **Export preflight geometry.** The geometry preflight stays on the default policy: nothing in
  the rendered HTML carries `data-slide-number`, so it never read per-slide geometry anyway
  (noted in section 1, out of scope).
- **Outline agent boundary.** `outline_by_mode` reaches the outline agent through a structural
  protocol and one request object (`generate_outline_for(SizedOutlineRequest)`), so the
  application layer gains no import of `agents`.
- **Workflow start regression (fixed).** Holding the project ORM row for the persona fallback
  made the editorial ACL re-read an expired `updated_at` outside the async greenlet (500 on
  `workflow/start`). The route now reads only `persona_id`.
- **Insights.** One Graph call per post asks for all metrics; if Graph refuses the list
  (a metric it does not offer for that media), each metric is asked alone and the refused one
  stays null. At most 10 Graph reads per dashboard request; the rest refresh on the next one.
- **Not wired, by design:** autopilot POV runs do not pick a slide-1 photo automatically (the owner
  binds one in the web UI before approval, else the hook slide renders without a photo).


## 11. PR #106 review amendments (2026-10-15)

- **Idempotent migrations.** Prod has no `alembic_version` table and the additive SQL is applied by
  hand, so `b0c1d2e3f4a5`, `b1c2d3e4f5a6` and `c2d3e4f5a6b7` add / create only what is missing
  (and the FK only when absent) and drop only what is present. A later `alembic upgrade` on prod
  is a no-op for them. `c2d3e4f5a6b7` stays the single head.
- **Persona and voice gate.** `ProjectSpec.persona_id` comes from `AUTOPILOT_PERSONA_ID`, else the
  newest persona named "Pedro" (case-insensitive), else None (logged as
  `autopilot.persona_unresolved`). The persona is stored on the carousel and loaded into the
  workflow start, so the content phase scores voice. A POV carousel with no voice score escalates
  with `persona_not_scored` (no revise: a revise cannot add a persona); Radar IA keeps AE-0364.
  The POV outline prompt receives the persona's voice, signature (preferred) and forbidden phrases
  (`persona_pov/v1/context.yaml`); a project with no persona gets an explicit empty context.
- **Slide-1 photo.** `POST /api/carousels` requires `hook_asset_id` for POV (422), checks it before
  insert (unknown 400, foreign 403) and binds/stages it after; the wizard sends it at create.
  `hook_face` raises `HookPhotoError` (`hook_photo_missing` / `hook_photo_unreadable`) instead of
  rendering slide 1 without the photo. The autopilot picks the owner's `hook` photo (most recently
  used, else newest, skipping one whose file is gone); with none, no carousel is created and the
  run fails with `hook_photo_missing` plus a Telegram upload request. Pose-tag matching was not
  built: nothing upstream (scout, run) names a pose yet.
- **Scheduling.** With `AUTOPILOT_DEFAULT_PUBLISH=now` (the default) a POV approve is scheduled for
  the next Tue/Thu 12:00 São Paulo slot (≥15 min ahead); Radar IA keeps the publish-now / schedule
  choice.
- **Scout POV choice.** Scout v3 sends `pov_format` (one of the four formats) and `slide_count`
  (8–10) per POV topic; the intake validates them (422) and stores them on `topic_candidates`
  (new nullable columns, folded into `b1c2d3e4f5a6`); the run falls back to `opiniao` / 9 only
  when they are absent. Radar IA topics never store them.
