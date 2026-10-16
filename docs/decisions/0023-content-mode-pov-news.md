---
status: proposed
date: 2026-10-16
decision-makers: Pedro Marins
consulted: Claude (AE-0406), GrokBot scout contract v2
informed: delivery team
---

# ADR-0023: Content mode `pov_news` (news analysis through the owner's point of view)

## Context and Problem Statement

ADR-0021 added "Ponto de Vista" (`pov`) next to Radar IA (`news_analysis`). The scout
(ADR-0020) finds AI news that would make good POV posts, but a plain `pov` deck argues an
opinion without first telling the reader what happened, and Radar IA is capped at one post a
week. The owner wants a third flavour: **the news, told through his point of view** — facts
first (what happened, who, when, from the sources), then why it matters to a software
developer, then his first-person read.

The scout also has something the backend does not: the exact words of the posts it read on
x.com. A quote card makes a news post credible, but a model that paraphrases or invents a
quote is a reputational risk.

How do we add the news-analysis voice and verified quotes without a second pipeline and
without letting the model alter or invent what someone said?

## Decision Drivers

- Reuse the POV contract, thesis step, validators and voice gate (no new pipeline).
- Existing `pov` and `news_analysis` runs keep their behaviour and prompts (prompts are
  immutable; existing clients of `POST /topics` must keep working).
- A quote shown on a slide must be a word-for-word piece of a post the backend stored, and
  its translations must be exactly the ones the scout supplied.
- The model never writes the source list, URLs or attribution.

## Considered Options

1. **A new pipeline** for news-through-POV, with its own contract and renderer.
2. **A `pov` sub-option** (e.g. `pov_format = noticia`) on the existing mode.
3. **A new content mode `pov_news` in the POV family**: same contract (`pov_hook_v1`),
   thesis step, validators and voice gate; its own prompt family; scout-verified quotes.

## Decision Outcome

Chosen: **Option 3**.

- `pov_news` is a member of the POV family (`POV_FAMILY_MODES`). Every branch that asks
  "is this a POV deck?" (thesis step, slide-1 photo, `pov_hook_v1`, role layouts, persona
  gate, Tue/Thu slot) takes it; branches that pick the **voice** (outline, hook, content and
  caption prompts) switch on the exact mode.
- New prompt family `carousel_pov_news/v1` (outline, hook, content, caption). `carousel_pov/v1`
  is untouched. `pov_format` is ignored for `pov_news` (stored as the default `opiniao`, which
  only picks the point-slide layout).
- **Quotes are data, verified at intake** (spec §4): the URL is a canonical X status URL listed
  in `sources` and stored through `POST /x-signals`; the excerpt is a substring of the stored
  post text after a fixed normalisation (NFC, curly→straight quotes, whitespace runs→one
  space, trim). A quote problem rejects only that topic, with `index` and `field` on the
  rejection.
- The quotes ride the topic → run → project (`pov_quotes`), with the topic's `sources`
  (`pov_sources`). The content prompt receives them as verified data; a deterministic
  validator blocks any slide whose quote card text is not exactly a supplied `text_pt`
  (PT) / `text_en` (EN), or more than two quote cards per deck. The attribution (initial
  circle, name, `@handle · X`) is rendered from the stored quote, never from model text, and
  never shows a URL.
- The caption footer `Fontes: @handle, domain.com` is appended by code from `pov_sources`.
- Caps: `pov_news` counts toward the daily cap, not the weekly Radar IA cap.

### Consequences

- Good, because POV safety rails (thesis confirmation, voice ≥70, presentation blockers)
  apply to news posts with no new gate code.
- Good, because a quote can only reach a slide verbatim from a stored post and the scout's
  own translations.
- Bad, because "POV family" vs "exact mode" is a distinction every future branch must make;
  `is_pov_family()` is the single helper for it and the branch list is recorded in AE-0406.
- Bad, because a quote shown in Portuguese is the scout's translation; fidelity of the
  translation is the scout's responsibility (spec §8), the backend only checks length.
- Neutral, because avatars and screenshots (spec §7) are phase 2.

## More Information

- Spec: GrokBot scout contract "POV News Mode Spec (v2)", 2026-10-16.
- Ticket: AE-0406. Related: ADR-0020 (autopilot), ADR-0021 (POV mode).
