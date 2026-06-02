# Carousel Closing Slide — Neon Shell v2.0

**Date:** 2026-06-01
**Context:** New closing slide replacing the CTA slide as the final carousel slide.

## Purpose

A persistent brand footer slide appended to every carousel. Displays the creator's avatar, name, Instagram handle, website URL, and a follow CTA. This slide replaces the previous "Call to Action" (Salvar/Compartilhar) slide.

## When to Apply

- The closing slide is **always the final slide** (replaces the CTA)
- Slide counter shows `N/N` where N = total slides including this one
- Counter dots show all previous slides as `past`, this one as `active`

## Layout

```
┌──────────────────────────────────┐
│                                  │
│          ╭──────╮                │
│          │avatar│                │
│          ╰──────╯                │
│                                  │
│     Pedro Marins                 │
│     @pedromarins.ai              │
│                                  │
│   ┌──────────────────────┐       │
│   │  marrinssolutions.com │       │
│   └──────────────────────┘       │
│                                  │
│   Siga para mais conteúdo        │
│   como esse                      │
│                                  │
│  [Creator Watermark]             │
└──────────────────────────────────┘
```

## CSS Classes

```css
.slide-closing {
  text-align: center;
  align-items: center;
  justify-content: center;
}
.slide-closing.slide-content { padding: 48px 36px 40px; }

.closing-avatar {
  width: 72px; height: 72px; border-radius: 50%;
  overflow: hidden; margin-bottom: 14px;
  border: 2px solid var(--primary);
  box-shadow: 0 0 16px var(--primary-dim);
}
.closing-avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }

.closing-name {
  font-family: var(--font-heading);
  font-size: clamp(20px, 4vw, 24px);
  font-weight: 800;
  color: var(--text);
  line-height: 1.2;
  margin-bottom: 2px;
}

.closing-handle {
  font-family: var(--font-mono);
  font-size: clamp(12px, 2.2vw, 14px);
  color: var(--text-60);
  margin-bottom: 20px;
}

.closing-website {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  border-radius: 6px;
  background: linear-gradient(135deg, var(--primary) 0%, #7c3aed 100%);
  color: #fff;
  font-family: var(--font-heading);
  font-size: clamp(13px, 2.4vw, 15px);
  font-weight: 700;
  text-decoration: none;
  margin-bottom: 18px;
  box-shadow: 0 0 20px var(--primary-dim);
}
.closing-website svg { width: 16px; height: 16px; }

.closing-cta {
  font-family: var(--font-mono);
  font-size: clamp(10px, 1.8vw, 12px);
  color: var(--text-55);
  letter-spacing: 1px;
}
```

## HTML Structure

```html
<div class="ig-post">
  <div class="ig-slide">
    <div class="ig-slide-inner">
      <div class="bg-glow"></div>
      <div class="slide-content slide-closing">
        <div class="slide-number">N/N</div>
        <div class="closing-avatar">
          <img src="../images/about-pedro.png" alt="Pedro Marins" />
        </div>
        <div class="closing-name">Pedro Marins</div>
        <div class="closing-handle">@pedromarins.ai</div>
        <div class="closing-website">
          <svg><!-- link icon --></svg>
          marrinssolutions.com
        </div>
        <p class="closing-cta">Siga para mais conteudo como esse</p>
      </div>
      <div class="creator-watermark">...</div>
    </div>
  </div>
  <div class="slide-counter">
    <div class="counter-dots">
      <span class="counter-dot past"></span>
      ...
      <span class="counter-dot active"></span>
    </div>
    <span class="counter-label">N/N</span>
  </div>
</div>
```

## Export Font Sizes (Instagram)

When exporting via Playwright at 1080x1350, inject these clamp overrides:

```css
.closing-name     { font-size: clamp(22px, 4.5vw, 52px) !important; }
.closing-handle   { font-size: clamp(14px, 2.5vw, 30px) !important; }
.closing-website  { font-size: clamp(15px, 2.8vw, 34px) !important; padding: 14px 32px !important; }
.closing-cta      { font-size: clamp(12px, 2.2vw, 26px) !important; }
```

## Agent Refactoring Todos

- [ ] Add `_render_closing_slide()` to `backend/src/rag_backend/application/services/carousel_template/slides.py`
- [ ] Wire it into `build_carousel_html()` in `html_template.py` — append as final slide
- [ ] Update slide counter increment in template to account for closing slide
- [ ] Update counter dots to N+1 dots
- [ ] Make avatar URL configurable via project settings (not hardcoded `/about-pedro.png`)
- [ ] Make handle and website URL configurable via project settings
- [ ] Add i18n support for "Siga para mais conteúdo como esse" text (PT/EN constants)
- [ ] Remove old CTA slide rendering (replaced by closing slide)
- [ ] Update all existing carousels to include closing slide
- [ ] Document closing slide in design system docs
