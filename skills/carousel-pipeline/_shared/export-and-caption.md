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

Generate caption with this structure:

1. **Hook** (1-2 lines with emoji): Attention-grabbing opener
2. **Value promise** (2-3 lines): What the reader will learn
3. **Comment question** (1 line): Engagement prompt
4. **Double CTA:** "Salve este post" + "Compartilhe com quem precisa"
5. **Hashtags** (12-18): Mix of Portuguese and English, niche-specific

### Caption style

- Informal Brazilian Portuguese
- Use relevant emojis
- No em dashes
- Direct and assertive
- Always end with engagement question

### Example

```
🧠 5 coisas que todo dev precisa saber sobre IA em 2026

A corrida por modelos mais eficientes esta mudando tudo. Se voce e dev, estas mudancas vao afetar seu trabalho direto.

Comente: qual dessas tendencias voce ja esta acompanhando?

Salve este post para consultar depois
Compartilhe com quem precisa ficar atualizado

#IA #MachineLearning #DevLife #TechTrends #InteligenciaArtificial #SoftwareEngineering #FutureOfWork #Codigo #Programacao #AI2026 #DeepLearning #TechBR
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
