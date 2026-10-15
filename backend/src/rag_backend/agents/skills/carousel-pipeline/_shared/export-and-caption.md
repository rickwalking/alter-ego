# Export and caption

Playwright assembly, Instagram caption structure, and blog markdown rules.

## Assembly and export

Use `CarouselExportTool` (Playwright screenshots) to render each slide.

### Playwright screenshot process

1. Write self-contained HTML file to `{output_dir}/carousel.html`
2. Launch Chromium browser via Playwright
3. Navigate to `file://{html_path}`
4. Wait 4 seconds for full render
5. Inject CSS overrides via `page.evaluate()` for font clamp values tuned to 1080px canvas
6. Locate all `.ig-slide-inner` elements (fallback to `.slide` for legacy templates)
7. Screenshot each slide at **1080×1350**, quality **95 JPEG**
8. Save as `{output_dir}/slide_{n}.jpg`

### CSS injection at export time

The export service injects CSS overrides to ensure fonts scale correctly on the 1080px canvas:

```css
.ig-feed { max-width: 1150px !important; }
.ig-slide-inner {
  width: 1080px !important;
  height: 1350px !important;
}
.s1-title { font-size: clamp(26px, 5.5vw, 56px) !important; }
.slide-heading { font-size: clamp(20px, 4.5vw, 50px) !important; }
.body-p { font-size: clamp(12px, 2.5vw, 30px) !important; }
```

This injection is performed via `page.evaluate()` so the original HTML template stays untouched.

### Export requirements

- Dimensions: **1080×1350** (Instagram portrait) — every slide, no exceptions
- Quality: 95 JPEG (optionally 100)
- Embed images as base64 data URIs in self-contained HTML
- Each slide is a self-contained unit
- Final output: individual JPG files and source HTML
- Optional 2x HD export: **2160×2700** with `deviceScaleFactor: 2` and scaled font clamps

**Anti-pattern:** CTA slide exported at wrong height when slide-level `height: 100%` collapses layout. See [`anti-patterns.md`](anti-patterns.md).

## Output artifacts

- Carousel project record with bilingual blog, design tokens, and status
- Generated slide images at `{output_dir}/images/`
- Exported JPG files at `{output_dir}/slide_{n}.jpg`
- Design tokens accessible via API for frontend consumption

## Blog markdown rules

- Full blog post in both pt-BR and en markdown (`blog_pt`, `blog_en`)
- Short paragraphs (2-4 sentences max)
- No em dashes — see [`text-formatting.md`](text-formatting.md)
- `<strong>` for key terms/numbers; `` `code` `` / `.code-tag` for technical terms
- Same depth and structure across both locales

## Instagram caption structure

Generate caption with this structure (AE-0372, prompt `carousel/v7/caption_prompt.yaml`;
the v2 structure below it is kept only for history):

1. **Hook** (line 1): the slide 1 hook again, no leading emoji
2. **Take** (2-4 short lines): what it changes in practice, from the slides only
3. **Question** (1 line): invites disagreement or the reader's own experience
4. **One CTA** by `cta_goal`: follow, send, or comment. Never "Salve" + "Compartilhe" together
5. **Search keywords** in plain text (e.g. "inteligência artificial", "IA para programadores")
6. **Hashtags** (3-5): mostly Portuguese (#inteligenciaartificial #IA #programacao + 1-2 niche)

Superseded v2 structure: emoji hook, value promise, comment question, double CTA
("Salve este post" + "Compartilhe com quem precisa"), 12-18 PT/EN hashtags.

### Caption style

- Informal Brazilian Portuguese, first person when it is the owner's take
- At most 2 emojis in the whole caption
- No em dashes
- Direct and assertive
- Never invent numbers, tests, results or experiences that are not on the slides

### Example (shape only; every claim must come from the slides)

```
Pare de pedir código pra IA. Peça isso no lugar.

O gargalo não é gerar código, é decidir o que construir.
Nos slides: as perguntas que eu faço antes de abrir o chat.

Qual dessas você já faz? Discorda de alguma?

Manda pra quem ainda pede "faz um app pra mim".

inteligência artificial, IA para programadores

#inteligenciaartificial #IA #programacao #engenhariadesoftware
```

## Editorial workflow API (unified path)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/carousels` | Create carousel project |
| GET | `/api/carousels` | List all carousels |
| GET | `/api/carousels/{id}` | Get project details |
| POST | `/api/carousels/{id}/workflow/start` | Start editorial workflow |
| POST | `/api/carousels/{id}/workflow/resume` | Human approve/revise at gate |
| GET | `/api/carousels/{id}/workflow/stream` | SSE progress and review events |
| GET | `/api/carousels/{id}/preview/*` | Authenticated workspace preview (never public-cacheable) |
| GET | `/api/carousels/{id}/blog` | Get blog (default pt-BR) |
| GET | `/api/carousels/{id}/blog/{lang}` | Get blog in specific language (pt/en) |
| GET | `/api/carousels/{id}/blog/{lang}?include_design=true` | Blog + design tokens |
| GET | `/api/carousels/{id}/design` | Get visual design tokens |
| GET | `/api/carousels/{id}/images/{filename}` | Serve carousel image |
| POST | `/api/carousels/{id}/caption` | Generate Instagram caption |
| GET | `/api/carousels/{id}/download` | Download files (ZIP) |
| DELETE | `/api/carousels/{id}` | Delete project and files |

**Removed:** legacy `/generate`, `/stream`, `/status`, `/resume` on carousels as public API paths.

## Final review approval vs publish

- **Approve** at `final_review`: sets `approved_for_publish`, `quality_passed: true`. Does **not** set `is_public`.
- **Publish:** separate explicit action via `POST /publish` or publish panel after final approval.
