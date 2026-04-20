# Carousel Pipeline Workflow

## System Prompt

You are a professional content strategist, visual designer, and Instagram carousel expert. You produce deep, fact-checked information in Brazilian Portuguese with an informative, assertive, direct tone. You NEVER use em dashes. You take creative initiative and explain every decision.

## Input Schema

```yaml
title: string           # Working title (MUST improve if weak)
audience: string        # e.g., "AI, software developers, architects"
niche: string           # e.g., "AI/Tech", "Cybersecurity"
slides: string          # e.g., "1 intro, 3 content, 2 closing"
aspect_ratio: string    # Default: "1080x1350 (Instagram portrait)"
sources: list[string]   # URLs to X posts, GitHub issues, blog posts
language: string        # Default: "pt-BR" (Brazilian Portuguese)
generate_images: bool   # Default: true
```

## Phase 1: Research

### Agent Dispatch

Launch 3-4 parallel research agents, each targeting different source types:

**Agent 1: Twitter/X & Primary Sources**
- Use Playwright MCP: `browser_navigate` to each source URL
- `browser_snapshot` to extract visible content
- Focus on tweets, threads, and primary announcements
- Extract: quotes, statistics, key claims with attribution

**Agent 2: News & Blog Articles**
- Use WebSearch to find recent articles about the topic
- WebFetch top 5-8 results from tech publications
- Focus on: TechCrunch, Ars Technica, The Verge, Wired, MIT Technology Review
- Extract: factual claims, expert opinions, data points

**Agent 3: Reddit & Community**
- Search r/programming, r/ClaudeAI, r/LocalLLaMA, Hacker News
- WebFetch top discussions and comments
- Extract: community reactions, practical insights, common questions

**Agent 4: Technical Sources** (if applicable)
- Search GitHub issues, CVEs, vendor security advisories
- Extract: technical details, code examples, impact assessments

### Research Output

Store each source as a `ResearchSource` entity with:
- `source_url`: The URL
- `source_type`: twitter/blog/reddit/github/news/documentation
- `title`: Page title
- `extracted_content`: Key content (max 10000 chars)
- `relevance_score`: 0.0-1.0

## Phase 2: Title Optimization

### Criteria

- Scroll-stop power: Does it make someone stop scrolling?
- Emotional pull: Does it trigger curiosity, urgency, or surprise?
- Length: Maximum ~60 characters
- Concrete > generic: Specific claims beat vague statements
- No clickbait: Promise must be delivered in content

### Process

1. Feed research context + working title to LLM
2. If original title is strong enough, keep it
3. If weak, propose 3 alternatives with rationale
4. Return: `{title, subtitle}` or `{title_pt, title_en, subtitle_pt, subtitle_en}`

### Example Weak to Strong

| Weak | Strong |
|------|--------|
| "AI News This Week" | "3 AI Models That Changed Everything This Week" |
| "Python Tips" | "5 Python Tricks Senior Devs Use Daily" |
| "Cybersecurity Update" | "This Zero-Day Affects 90% of Web Apps" |

## Phase 3: Content Synthesis

### Bilingual Output

The LLM MUST return JSON with both languages:

```json
{
  "slides": [
    {"number": 1, "type": "intro", "heading": "...", "body": "...", "image_prompt": "..."}
  ],
  "blog_pt": "# Title\n\nFull blog post in Brazilian Portuguese markdown...",
  "blog_en": "# Title\n\nFull blog post in English markdown...",
  "title_pt": "Portuguese Title",
  "title_en": "English Title",
  "subtitle_pt": "Portuguese Subtitle",
  "subtitle_en": "English Subtitle"
}
```

### Writing Rules

**Portuguese (pt-BR):**
- Informal but professional tone
- Engaging and direct
- Use emojis sparingly
- Short paragraphs (2-4 sentences max)

**English (en):**
- Professional, direct tone
- Same depth and structure as Portuguese version
- No colloquialisms

**Universal Rules:**
- NEVER use em dashes in either language. Use periods, commas, parentheses, or conjunctions
- `<strong>` for key terms and numbers
- `.code-tag` for technical terms
- Image prompts must describe comic/manga style scenes (no text in images)

### Slide Structure

| # | Type | Content | Image |
|---|------|---------|-------|
| 1 | intro | Hook + thesis statement | Hero image |
| 2 | content | Key insight #1 with data | Supporting visual |
| 3 | content | Key insight #2 with quote | Supporting visual |
| 4 | content | Key insight #3 with example | Supporting visual |
| 5 | closing | Actionable takeaways | Summary visual |
| 6 | cta | Save + share prompt | Brand/CTA visual |

## Phase 4: Design System

### Theme Resolution

If theme is "auto", select the most appropriate theme based on topic analysis:
- Security/attacks -> cybersecurity
- AI models/competitions -> ai_competition
- Dev skills/tutorials -> developer_skills
- Code/leaks/open source -> source_code
- Social engineering/phishing -> social_engineering

### Theme Palettes

| Theme | Primary | Accent | Background |
|-------|---------|--------|------------|
| cybersecurity | #ef4444 | #00d4ff | #0a0e17 |
| ai_competition | #3b82f6 | #f59e0b | #0a0e17 |
| developer_skills | #0ac5a8 | #8b5cf6 | #080c12 |
| source_code | #a855f7 | #f97316 | #0c0a14 |
| social_engineering | #f59e0b | #ef4444 | #0a0c14 |

### Design Tokens Structure

```json
{
  "colors": {
    "primary": "#3b82f6",
    "accent": "#f59e0b",
    "bg": "#0a0e17",
    "text": "#ffffff",
    "text_muted": "rgba(255,255,255,0.63)",
    "text_dim": "rgba(255,255,255,0.48)",
    "border": "#3b82f633",
    "glow": "#3b82f60D"
  },
  "typography": {
    "font_family_heading": "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
    "font_family_body": "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
    "font_family_badge": "'Courier New', monospace"
  },
  "images": {
    "hero": "/api/carousels/{id}/images/hero",
    "slides": ["/api/carousels/{id}/images/slide_1", ...]
  },
  "layout": {
    "badge_label": "AI Education",
    "swipe_text": "Desliza" (or "Swipe"),
    "progress_segments": 6
  }
}
```

### HTML Template

Build self-contained HTML with:
- Inline CSS using design tokens as CSS custom properties
- Embedded images as base64 data URIs
- Dark background with glow effects
- Responsive 1080x1350 slide dimensions
- Progress bars on content slides
- Badge showing niche category on intro slide

## Phase 5: Image Generation

### Image Generation Service

Use `ImageGenerationTool` which wraps Google Gemini `gemini-3.1-flash-image-preview` via `google-genai` SDK.

### Image Prompt Guidelines

Each image prompt must specify:
- **Style**: Comic/manga illustration style
- **Aspect ratio**: 3:1 (wide format for slide embedding)
- **No text**: No words, letters, or numbers in the image
- **Dark theme**: Dark background with accent color highlights
- **Subject**: Concrete visual metaphor for the slide content

Example prompt: "Comic manga style illustration of a neural network transforming data streams, dark background with blue and gold accents, futuristic digital landscape, no text, no letters"

### Rate Limiting

Add 2-3 second delay between API calls to avoid rate limits. Generate 1 image per content-heavy slide (typically 4 total).

## Phase 6: Assembly & Export

### Playwright Screenshot Process

1. Write self-contained HTML file to `{output_dir}/carousel.html`
2. Launch Chromium browser via Playwright
3. Navigate to `file://{html_path}`
4. Wait 4 seconds for full render
5. Locate all `.slide` elements
6. Screenshot each slide at 1080x1350, quality 95 JPEG
7. Save as `{output_dir}/slide_{n}.jpg`

### Export Process

- Embed images as base64 data URIs in the HTML
- Each slide is a self-contained unit
- Final output: individual JPG files and the source HTML

## Phase 7: Caption Generation

### Caption Structure

1. **Hook** (1-2 lines with emoji): Attention-grabbing opener
2. **Value promise** (2-3 lines): What the reader will learn
3. **Comment question** (1 line): Engagement prompt
4. **Double CTA**: "Salve este post" + "Compartilhe com quem precisa"
5. **Hashtags** (12-18): Mix of Portuguese and English, niche-specific

### Style

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

## Error Handling

At any phase, if an error occurs:
1. Update project status to FAILED with error message
2. Save partial results (slides, blog content generated so far)
3. Log the specific phase and error details
4. Return structured error to the user with guidance on retry