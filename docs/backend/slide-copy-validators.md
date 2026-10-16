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
| `wrong_language` | PT copy that reads as English, EN copy as Portuguese (4+ words, 2+ other-language stopwords outnumbering its own) | model fix |
| `repeated_text` | the same sentence twice in one slide, a doubled word ("o o", "the the"; "had had" is fine) | doubled word collapsed |
| `structured_item_split` | an item title ending on "ou", "e", "de", "com", "or", "and", "of", "with" | model fix; the outline fill no longer cuts a key point there |

Legit copy is never flagged: `**bold**` (PT) and balanced `<strong>` (EN) emphasis, proper
nouns, numbers, first-person Portuguese. The existing `heading_repeated_in_body` also blocks a
POV hook whose body repeats its heading (prod slide 1).

The EN casing repair never capitalizes a word after a mid-sentence colon ("decide: pass or
return"); proper nouns, "I" and acronyms keep their capitals.

The repair runs in the generation-time review repair and in the owner/gate autofix plan.

## Autopilot autofix

See [`docs/architecture/grokbot-autopilot.md`](../architecture/grokbot-autopilot.md) "Model
fix, then escalate". In short: deterministic repair, then up to 3 model attempts per failing
slide (blocking rule or voice score under 70), then approve or escalate. Never a revise.

| Setting | Default | Meaning |
|---|---|---|
| `AUTOPILOT_AUTOFIX_ATTEMPTS` | 3 (`AUTOFIX_MODEL_ATTEMPTS`) | model attempts per failing slide |
| `CONTENT_DRAFT_CONCURRENCY` | 4 | slides fixed in parallel |
