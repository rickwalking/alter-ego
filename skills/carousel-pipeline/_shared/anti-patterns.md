# Anti-patterns

Learned from broken production runs. Phase agents must recognize these symptoms and apply the fixes — do not repeat them.

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| Content drifts away from the user's actual topic (e.g., Uncle Bob's AI tweet → generic *Clean Coder* content) | User-provided `sources` ignored; DDG-only search returns the broadest-popular results for the topic string | User sources are **authoritative** — scrape first at higher relevance; DDG only supplements |
| Generated images have speech bubbles / warm dojo lighting / grid panels | LLM was allowed to specify style/ratio/layout in `image_prompt` | Treat `image_prompt` as **scene description only**; wrap with mandatory directives server-side (see [`image-generation.md`](image-generation.md)) |
| Pipeline marks `completed` but blog is empty and only one intro slide saved | JSON parse failed and code silently fell back to a stub | `_extract_json` strips ` ```json ` fences and prose around JSON; on failure, **raise** |
| Slide 5 is a long paragraph floating at the top of an empty canvas | Content LLM returned prose instead of checklist structure | Closing slide must render as **checklist with icons**, not a paragraph (see [`content-contracts.md`](content-contracts.md)) |
| Intro slide has no hero image | Phase 5 filtered to `slide_type == 'content'` only | Intro + content slides get images; closing + CTA don't |
| Body text feels cramped / closing slide is a wall of prose | The content LLM returned a plain paragraph for a slide that should be a structured list | Require a `features` array on closing (and stat-heavy content) slides; render via `.feature-grid`. Do NOT shrink the font to make prose fit. |
| Intro footer sits right against the subtitle instead of pinned to the bottom | `.s1-main` missing `flex: 1` | Keep `.s1-content { display: flex; flex-direction: column; height: 100% }` AND `.s1-main { flex: 1 }` so the footer gets pushed to the bottom |
| Title/body contains em dashes (`—`/`–`) — the classic AI-writing tell | The content LLM ignores prompt-level bans | Ban em dashes in the prompt AND strip them defensively in the renderer (`_render_inline` replaces `—`/`–` with a period) |
| `**bold**` appears literally instead of bold text | Renderer was treating body as plain text | Run body through an inline renderer that escapes HTML, strips dashes, and converts `**text**` → `<strong>text</strong>` |
| CTA slide is exported at 1080×880 instead of 1080×1350 (crops weirdly in Instagram) | `.cta-slide { height: 100% }` overrode `.slide { height: 1350px }` and collapsed to intrinsic content height because `<body>` had no fixed height | Remove `height: 100%` from `.cta-slide` (and any slide-level class). All six slides must render at **exactly 1080×1350**; Playwright screenshots the element's own bounding box, so any slide with a collapsed height ships wrong to Instagram |
| Research approval triggers outline generation in the service layer | Approve-before-generate ordering; generation runs outside the target phase node | Generate at **phase enter**, not on prior phase approval in `resume` handler |
| Content/design gates show empty review panels | Generation runs at wrong time relative to `interrupt()` | All artifacts must exist **before** `phase_status: awaiting_human` |
| `/workflow/resume` blocks for tens of seconds | Heavy AI work in resume handler (`_prepare_phase_before_resume`) | Resume handler persists human input only; generation runs inside graph nodes |
| Infinite `/stream` polling loop | Legacy stream polled while editorial workflow idle | Use unified `GET /workflow/stream`; no progress polling at `awaiting_human` |
| Final review approval sets blog public automatically | Editorial sign-off conflated with publish | Approve sets `approved_for_publish`; publish is a separate explicit action |
