# Carousel f2231ece Lower-Third Correction Plan

## Scope

Correct the generated carousel artifacts for project
`f2231ece-7903-4c93-a89c-a459459fdaa5` without regenerating or changing the
background images.

Preserve:

- generated artwork and image crop
- red/cyan palette and gradients
- font family, text colors, and slide counters
- seven-slide sequence and closing-card design

Change only:

- copy length and editorial cleanup on slides 1-6
- vertical placement of the hero copy block
- `marrinssolutions.com` to `marinssolutions.com` on slide 7
- restore Pedro's portrait as the slide 7 avatar

## Evidence

The rendered PT PDF shows strong art direction, but slides 1-6 read as articles
placed over artwork rather than lower-third hero captions.

The generated HTML explains the failure:

- `.slide-hero-content` already uses `justify-content: flex-end`.
- `.slide-hero-main` allows nearly the full slide height with
  `max-height: calc(100% - 112px)`.
- the export CSS expands that allowance to `calc(100% - 190px) !important`.
- several bodies repeat the heading and contain 10-30 visual lines.
- slide 4 includes editorial scaffolding (`SLIDE 4` and `TÍTULO:`).
- the closing-slide HTML references `images/about-pedro.jpg`, but that asset is
  absent from the carousel's shared `images/` directory.

The primary defect is therefore copy density. Positioning needs a lower-third
constraint, but it must not hide or clip long text.

The slide 7 avatar defect is an asset-staging failure, not a CSS failure. The
canonical portrait is a valid 1122x1402 JPEG at:

```text
/home/pmarins/projects/alter-ego/frontend/public/about-pedro.jpg
```

Its SHA-256 is:

```text
620c45fe5feff936a605a818ad5375184942a0eceab8cec56c85a24a1d6d4f00
```

## Files To Edit Directly

Back up these generated files before editing:

```text
/app/output/carousels/f2231ece-7903-4c93-a89c-a459459fdaa5/pt/carousel.html
/app/output/carousels/f2231ece-7903-4c93-a89c-a459459fdaa5/en/carousel.html
/app/output/carousels/f2231ece-7903-4c93-a89c-a459459fdaa5/pt/hd/carousel.html
/app/output/carousels/f2231ece-7903-4c93-a89c-a459459fdaa5/en/hd/carousel.html
```

Stage the canonical avatar at:

```text
/app/output/carousels/f2231ece-7903-4c93-a89c-a459459fdaa5/images/about-pedro.jpg
```

The existing relative references are correct and should remain:

```text
PT/EN standard HTML: ../images/about-pedro.jpg
PT/EN HD HTML:       ../../images/about-pedro.jpg
```

Apply equivalent semantic edits in PT and EN. The languages should have the
same hierarchy and approximate line count, not necessarily literal
line-for-line translations.

## Layout Changes

Append a carousel-specific override to all four HTML files:

```css
.slide-1-main,
.slide-hero-main {
  flex: 0 0 auto !important;
  margin-top: auto !important;
  max-height: 42% !important;
}

.slide-1-content,
.slide-hero-content {
  justify-content: flex-end !important;
}
```

Do not add `overflow: hidden`. Copy must be shortened until it fits naturally;
clipping would conceal a failed edit.

When rendering through `PlaywrightExportService`, pass the same declarations
through `ExportConfig.css_overrides`. The default export injection adds
`!important` rules after the document CSS, so editing only the document
stylesheet is not sufficient for exported JPEGs.

Expected composition:

- top 55-60%: unobstructed focal artwork
- bottom 35-42%: number, title, and concise supporting copy
- footer reserve: watermark or `Swipe`, without collision

## Copy Contract

At the 1080x1350 export size:

- title: maximum 2-3 rendered lines
- body: maximum 5-7 rendered lines
- body blocks: maximum 3 concise points
- no heading repeated as the first body line
- no document scaffolding, source labels, dividers, or next-slide instructions
- no `<br><br>` between every sentence
- no em dashes; use periods, commas, or colons
- no emojis or decorative symbols in titles or body copy

If a slide cannot meet this contract, move supporting detail to the Instagram
caption. Do not reduce the font size to preserve article-length copy.

## Slide Edit Matrix

### Slide 1, Intro

Keep the current headline. Replace the body with one setup sentence and one
risk sentence. Remove the repeated alert headline, three-arrow list, and final
restatement.

PT direction:

> A Anthropic quer limitar pesquisas em que agentes modificam os próprios
> processos sem supervisão. O risco: capacidades podem acelerar mais rápido do
> que humanos conseguem auditar.

EN direction:

> Anthropic wants limits on research where agents modify their own processes
> without supervision. The risk: capabilities may accelerate faster than
> humans can audit them.

### Slide 2, Why It Matters

Remove the heading duplicated in `<strong>`. Keep three compact ideas:
early self-optimization, unpredictable capability jumps, and evaluation before
autonomous improvement.

### Slide 3, Definition

Replace the glossary-style article with a two-sentence definition and contrast
with supervised fine-tuning. Remove dividers, risk levels, source URL, and the
repeated question.

### Slide 4, Technical Risks

Delete `SLIDE 4`, `TÍTULO:`, the repeated title, and the source URL. Keep three
one-line risks:

- misalignment reduces the detection window
- opacity makes each cycle harder to audit
- rollback mechanisms can be changed or removed

### Slide 5, Safer Path

Keep three guardrails only:

- interpretability checks before experiments
- isolated, resource-limited sandboxes
- automatic interruption plus independent review

Remove the repeated title, five long explanations, closing restatement, and
next-slide instruction.

### Slide 6, Practical Actions

Remove the repeated title. Keep three direct actions:

- audit agents that can change prompts, memory, or evaluation criteria
- log every self-improvement decision
- adopt emerging standards and participate in governance

### Slide 7, Closing

Keep the design unchanged. Copy the canonical portrait from:

```text
frontend/public/about-pedro.jpg
```

to the carousel's shared asset directory:

```text
/app/output/carousels/f2231ece-7903-4c93-a89c-a459459fdaa5/images/about-pedro.jpg
```

Do not generate, crop, darken, or substitute the portrait. Let
`.closing-avatar img { object-fit: cover; }` produce the circular crop from the
original image.

Also replace:

```text
marrinssolutions.com
```

with:

```text
marinssolutions.com
```

in PT and EN HTML.

## Rendering Sequence

1. Back up the four generated HTML files.
2. Copy `frontend/public/about-pedro.jpg` into the carousel's shared `images/`
   directory as `about-pedro.jpg`.
3. Verify the copied file's SHA-256 matches the canonical source.
4. Apply the PT and EN copy replacements.
5. Apply the lower-third CSS override to standard and HD HTML.
6. Re-render PT and EN standard JPEGs from the edited standard HTML.
7. Re-render PT and EN HD JPEGs from the edited HD HTML.
8. Rebuild both PDFs from the corrected standard JPEGs.
9. Do not call the image-generation provider. Reuse the six existing files in
   the shared `images/` directory.

## Acceptance Checks

- all PT and EN slides remain 1080x1350; HD remains 2160x2700
- slides 1-6 expose at least the upper 55% of each image without text
- no title/body duplication remains
- no body exceeds seven rendered lines at standard export size
- no emojis or dash punctuation remain in visible slide text
- no copy is clipped or hidden
- slide 2 watermark and `Swipe` remain visible and do not collide with copy
- all slide counters remain unchanged
- both closing slides show `marinssolutions.com`
- `images/about-pedro.jpg` exists, is a decodable JPEG, and matches the
  canonical source hash
- the PT and EN standard and HD HTML references resolve to the staged avatar
- slide 7 shows Pedro's face inside the circular avatar at both resolutions;
  no broken-image icon, blank circle, or near-black placeholder is visible
- PT and EN PDFs contain seven pages
- a contact sheet review confirms consistent lower-third alignment across both
  languages

## Out Of Scope

- image prompt changes or new OpenAI image calls
- palette, font, background crop, counter, or closing-card redesign
- global carousel template changes for unrelated projects
