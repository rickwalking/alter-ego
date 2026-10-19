# Slide copy validators and the autopilot autofix (AE-0401)

Deterministic, blocking presentation rules for visible slide copy, PT and EN, on the
heading, the body and every structured item (features, summary points, actions). They are
active only on contracts that declare a severity for them: `pov_hook_v1` (POV) and
`hero_lower_third_v4` (Radar IA). `hero_lower_third_v1`-`v3` keep their semantics.

Code: `application/services/carousel/presentation_copy_rules.py` (rules),
`copy_hygiene_text.py` (detectors), `copy_hygiene_repair.py` (deterministic repair). Codes
live in `domain/constants/carousel_presentation.py`.

## Rules

| Code | Fires on | Deterministic repair |
|---|---|---|
| `structured_payload_in_copy` | JSON/dict text, a code fence, a leaked `"heading":`/`"body":` key, `{"pt":` | a (fenced) bilingual object becomes that locale's heading, body and whole item lists; a fence around plain copy is dropped |
| `markup_leak` | an HTML tag other than `<strong>`, a Markdown heading (`#`), list or table syntax, inline backticks, literal `\n` / `\"` | `<b>` to `<strong>`, other tags dropped (text kept), leading `#` dropped (the whole line when it repeats the heading), backticks removed, escapes undone |
| `emphasis_unbalanced` | an odd number of `**`, an empty `****` or `<strong></strong>` | empty pair dropped, unpaired last `**` removed |
| `assistant_chatter` | "Here is the slide", "Sure,", "Claro! Aqui está o texto", "Assistant:", notes about the task | model fix |
| `placeholder_text` | `[insert …]`, `{topic}`, `TODO`/`TBD`/`FIXME` (case-sensitive), lorem ipsum, an ellipsis stub | model fix |
| `encoding_garbled` | mojibake (`Ã©`, `â€™`), U+FFFD, control characters | control characters removed, cp1252 mojibake decoded when it round-trips |
| `copy_truncated` | a body (not intro/CTA) ending without `.!?`, with `...`, `,`, `:` or a dangling connector | model fix |
| `body_too_short` | a content-slide body under 8 words (unless 3+ complete features carry the copy) | model fix |
| `wrong_language` | PT copy that reads as English, EN copy as Portuguese (4+ words, 2+ other-language stopwords outnumbering its own; EN copy also when the autofix's `looks_portuguese` matches: 1 PT stopword + an accented letter in 3+ words, AE-0413). Contracts without this rule (v3) report Portuguese EN copy as `translation_not_english` | model fix |
| `repeated_text` | the same sentence twice in one slide, a doubled word ("o o", "the the"; "had had" is fine) | doubled word collapsed |
| `structured_item_split` | an item title ending on "ou", "e", "de", "com", "or", "and", "of", "with" | model fix; the outline fill no longer cuts a key point there |

Legit copy is never flagged: `**bold**` (PT) and balanced `<strong>` (EN) emphasis, proper
nouns, numbers, first-person Portuguese. The existing `heading_repeated_in_body` also blocks a
POV hook whose body repeats its heading (prod slide 1).

The EN casing repair never capitalizes a word after a mid-sentence colon ("decide: pass or
return"); proper nouns, "I" and acronyms keep their capitals.

The repair runs in the generation-time review repair and in the owner/gate autofix plan.

## The rows render the validated copy (addendum 2)

The renderer, the export and the Telegram issue list read the `carousel_slides` rows, while
the gates validate the checkpoint's `localized_slides`. The rows used to be written from
`slide_drafts` (falling back to the long `draft_text`) and the localized copy reached them only
on owner edits, so prod 98a2e2f0 validated short copy and rendered 368-772 character bodies.
`localized_rows_sync.sync_rows_to_localized` now projects the localized copy onto the rows
every time it is built or changed: the content and design ensures, the gate repair and the
model fix (same commit as the CAS). Empty item lists are dropped on both sides
(`_symmetric_translation`), so a PT without `features` and an EN `features: []` no longer raise
`translation_shape_mismatch`.

Other fixes from the same run:

- The proper-noun vocabulary learns multi-word names whole ("Claude Code", "Grok Bot"), so
  "the code" or "the bot" is no longer reported as a lowercased proper noun.
- The POV hook sub-line budget is one line, 40 characters (`pov_hook_v1` `intro_subtitle`), so
  the hook copy never covers the owner's face. The model fix uses it as the hook's target.

## Autopilot autofix

See [`docs/architecture/grokbot-autopilot.md`](../architecture/grokbot-autopilot.md) "Model
fix, then escalate". In short: deterministic repair, then up to 3 fast-model attempts per
failing slide (blocking rule or voice score under 70), then up to 2 more on the reasoning model
(AE-0407), then approve or escalate. Never a revise.

| Setting | Default | Meaning |
|---|---|---|
| `AUTOPILOT_AUTOFIX_ATTEMPTS` | 3 (`AUTOFIX_MODEL_ATTEMPTS`) | fast-model attempts per failing slide |
| `AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS` | 2 (`AUTOFIX_ESCALATION_ATTEMPTS`) | reasoning-model attempts after them (0 = off; on deploy.yml as a GitHub variable) |
| `CONTENT_DRAFT_CONCURRENCY` | 4 | slides fixed in parallel |
| `AUTOPILOT_PERSONA_UNSCORED_MAX_TICKS` | 3 (`PERSONA_UNSCORED_MAX_TICKS`) | ticks a fixed slide may stay unscored before `persona_judge_unavailable` (AE-0433) |

### Unscored persona judge (AE-0433)

A judge call that times out or gives no score is not a verdict. The retry runs on the next
model of the fast role's queue (`as_fallback()`), because the judge's 120 s timeout equals one
queue model's timeout and the queue never got past its first model. When both calls give no
score, the rewritten slide keeps its old score in `persona_scores` with
`rescore_pending: true` and `unscored_ticks: N`. The gate still reads the old score, so the
autopilot step does not escalate `persona_score_below_threshold` with no failing slide: it
waits (`persona_rescore_pending`, run stays `generating`). On the next tick the slide's
current copy is re-scored before any rewrite: a passing score fixes it as it is, a low score
sends it back to the rewrite loop, and no score counts one more tick. Once a slide reaches
`AUTOPILOT_PERSONA_UNSCORED_MAX_TICKS`, the run escalates `persona_judge_unavailable`. The
voice floor (70) is unchanged.

## Content-gate targeted repair (AE-0430)

Prod carousel `5344b6c6` kept 12 blockers through two "Feedback para revisão" runs. Before
this, the only model step at the content gate was one whole-slide re-draft (fail-closed
chain), and it never saw the violations. Now, whenever the content ensure ends with a
blocking `content_gate_validation` (first drafting, translation, a revision), the runner
calls `content_gate_repair_flow.repair_blocked_content_gate`:

1. **Fill.** A PT structured field EN lacks (TL;DR, item list, a shorter list) is copied
   into EN, so `translation_shape_mismatch` cannot stay; each copied text becomes a
   "translate this" target.
2. **Targets.** One per blocking violation that names a slide, a locale and a visible
   text path (`heading`, `body`, `tldr_strip`, `<list>[n].title|body`). Each target carries
   the current text, the exact budget the validator enforces (`max_characters`,
   `max_lines`), the problems, the slide heading and, for EN, the PT source. Fields that
   pass are never sent, and answers for ids nobody asked for are ignored.
3. **One model call per round** (fast role, `carousel_gate_repair/v1/field_repair.yaml`,
   Langfuse-traced through the orchestrator's runnable config), answers patched in by path,
   re-validated. At most **2 rounds** (`GATE_REPAIR_MAX_ROUNDS`), at most 40 fields per round.
4. The repaired slides are written back like owner edits (`apply_localized_slide_edits`):
   drafts, EN translations and both reports stay in step. Nothing is truncated and no rule
   is loosened; whatever still blocks stays visible. A failing model changes nothing.

Code: `content_gate_repair.py` (loop + model adapter), `content_gate_repair_targets.py`
(fill, targets, patching), `content_gate_repair_flow.py` (runner hook, revision note).
Logs: `content_gate_repair_round`, `content_gate_repair_done`,
`content_gate_repair_model_failed`.

Related fixes from the same incident:

- **Translation keeps the shape.** The translator (`carousel/v8/slide_translations.yaml`)
  now receives and returns `tldr_strip` and the item texts; the parser gives every EN
  translation the PT draft's structured extras (translated when the answer has the same
  shape). An unanswered TL;DR stays absent, so the gate blocks on the shape and the repair
  translates it. The TL;DR strip is now language-checked like heading and body
  (`translation_not_english` when it equals the PT one, `wrong_language`), so a PT TL;DR can
  never pass as the EN one.
- **Label scaffolding.** `**PT**` / `**EN**` bold-only lines are locale section headers in
  the scaffold recovery (only `## PT` was), so `**PT**` no longer leaks into the PT body,
  and an EN payload built from the draft takes the EN section heading.
- **Manual editor.** The editable EN column offers every structured field PT has (empty),
  so a remaining violation is always fixable by hand.
