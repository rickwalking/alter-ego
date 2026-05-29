# Critical Rules

Canonical operational rules for all carousel pipeline phases. Phase skills reference this file; do not duplicate these rules in phase folders.

## Prerequisites

Before running generation, verify:

1. `GEMINI_API_KEY` is set (image generation)
2. `CAROUSEL_OUTPUT_DIR` is configured (defaults to `./output/carousels`)
3. Playwright Chromium is installed (`playwright install chromium`)
4. The backend API is running and accessible

## Language and tone

- **Primary language:** Brazilian Portuguese (informal but professional, engaging, direct).
- **Secondary language:** English (professional, direct; same depth and structure as pt-BR).
- **Bilingual storage:** Always generate both locales. Store in `blog_translations` (not a single-language field).
- **Em dashes:** NEVER use em dashes (`—` / `–`) in either language. Use periods, commas, parentheses, or conjunctions instead. See [`text-formatting.md`](text-formatting.md) for renderer defenses.

## Fact-checking

Every factual claim must have at least one authoritative source from the research phase.

**Common trap:** conflating *popularized* with *invented*. Example — Uncle Bob popularized the **SOLID acronym**, but LSP is Barbara Liskov's and OCP is Bertrand Meyer's. Always verify attribution before stating who invented or coined something.

## User sources are authoritative

User-provided `sources` in the generate request are **primary context**. They are scraped first at `relevance_score=2.0`; broad web search only *supplements* them up to a cap (10 total).

Without a user-provided URL, research can drift toward whatever the topic string surfaces (e.g., "Uncle Bob" → broad Clean Code results instead of the specific tweet). **Always pass the source URL when the carousel is about a specific post, tweet, or announcement.**

## Title criteria

- Scroll-stop power and emotional pull
- Maximum ~60 characters
- Concrete over generic
- No clickbait: the promise must be delivered in content
- If the original title is weak, propose 3 alternatives with rationale

## Design and images (system-enforced)

- **Image style:** Enforced server-side, not requested via LLM prompt. See [`image-generation.md`](image-generation.md).
- **Design tokens:** Every blog/carousel gets a unique, self-contained visual identity stored as structured tokens. The frontend is a theme consumer — never hardcoded palette values in UI code.

## Fail loudly

If content synthesis returns unparseable or empty output, **raise** — never silently mark the project `completed` with a stub slide.

JSON parsing tolerance: Anthropic frequently wraps JSON in ` ```json ... ``` ` fences or adds leading/trailing prose. The server uses `_extract_json` which strips fences and extracts the `{...}` substring before parsing. **If parsing still fails, the pipeline raises** — do not fall back to a stub slide. Log the raw response on failure so the prompt can be improved.

## Server-side search fallback

The backend uses the `ddgs` Python library (DuckDuckGo client with UA rotation and backend fallbacks). Do **not** scrape `google.com/search` or `html.duckduckgo.com/html/` directly from a server — Google blocks headless browsers and DDG's HTML endpoint returns 403 to server IPs.

## Status flow

```
PENDING -> RESEARCHING -> DRAFTING -> DESIGNING -> GENERATING_IMAGES -> EXPORTING -> COMPLETED
                                    └-> FAILED (at any phase)
```

Editorial workflow uses the same phase sequence with human review gates: `brief → research → outline → content → design → images → final_review`.

## Error handling

At any phase, if an error occurs:

1. Update project status to `FAILED` with error message
2. Save partial results (slides, blog content generated so far)
3. Log the specific phase and error details
4. Return structured error to the user with guidance on retry
