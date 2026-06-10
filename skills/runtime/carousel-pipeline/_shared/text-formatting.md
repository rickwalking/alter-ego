# Text formatting

Inline emphasis, heading highlights, and prose rules shared across outline, content, and caption phases.

## Universal writing rules

**Portuguese (pt-BR):**

- Informal but professional tone
- Engaging and direct
- Use emojis sparingly
- Short paragraphs (2-4 sentences max)

**English (en):**

- Professional, direct tone
- Same depth and structure as Portuguese version
- No colloquialisms

## Em-dash ban

NEVER use em dashes (`—` / `–`) in either language. Use periods, commas, parentheses, or conjunctions.

**Defense in depth:** Ban in prompts AND strip defensively in the renderer — `_render_inline` replaces `—`/`–` with a period.

## Two inline emphasis flavors

| Syntax | Use for | Renders as |
|--------|---------|------------|
| `**bold**` | Prose emphasis (phrases, stats, names) | `<strong>` — white in body text, accent-colored in headings |
| `` `code` `` | Technical tokens (package names, versions, file patterns, commands, config keys, env vars) | `<span class="code-tag">` — monospace pill in **primary** palette color with tinted background |

**Examples the renderer handles:**

- `` `axios`, `2.1.88`, `*.map`, `.npmignore` `` → primary-color code pills
- `**source map de 59.8 MB**` → white bold in body
- `**Kimi K2.6: 300 Agentes. **12 Horas**.**` → heading highlight in accent

Pick the right flavor per token: prose gets `**`, literal code/config gets backticks. Picking the wrong one loses the hierarchy reference carousels built.

Also use `<strong>` for key terms and numbers in markdown blog output; `.code-tag` for technical terms in rendered HTML.

## Heading accent highlights

Every slide heading marks **1-2 key words** with Markdown `**word**`. The renderer converts `<strong>` inside `.s1-title`, `.slide-heading`, and `.cta-title` to the palette's **accent** color (not white).

**Examples:**

- *Código do Claude Code **vazou**. O que descobrimos?*
- *As **features escondidas** que ninguém deveria ver*
- *O **impacto** e a reação da comunidade*
- *O que isso **significa** pra devs*

**Rules:**

- Never highlight an entire heading
- Never highlight more than two words — contrast breaks if half the title is accent-colored

## Inline renderer requirements

Body text must pass through an inline renderer that:

1. Escapes HTML entities
2. Strips em dashes
3. Converts `**text**` → `<strong>text</strong>`
4. Converts `` `code` `` → `<span class="code-tag">code</span>`

If `**bold**` appears literally on a slide, the renderer was treating body as plain text — fix the render path, not the LLM output alone.

## Caption and blog markdown

- Short paragraphs (2-4 sentences max)
- Informal Brazilian Portuguese for captions; assertive and direct
- No em dashes in captions or blog posts
- Relevant emojis in captions (hook section)
