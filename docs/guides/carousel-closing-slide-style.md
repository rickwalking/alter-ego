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
│   │  marinssolutions.com  │       │
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
.slide-closing.slide-content { padding: 48px 48px 40px; }

.closing-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: min(100%, 460px);
  padding: 28px 30px 32px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(6,10,18,0.88), rgba(6,10,18,0.64));
  border: 1px solid color-mix(in srgb, var(--primary), transparent 80%);
}

.closing-avatar {
  width: 112px; height: 112px; border-radius: 50%;
  overflow: hidden; margin-bottom: 18px;
  border: 3px solid var(--primary);
  box-shadow: 0 0 28px var(--primary-dim);
}
.closing-avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }

.closing-name {
  font-family: var(--font-heading);
  font-size: clamp(30px, 6vw, 44px);
  font-weight: 900;
  color: var(--text);
  line-height: 1.05;
  margin-bottom: 6px;
}

.closing-handle {
  font-family: var(--font-mono);
  font-size: clamp(16px, 2.8vw, 20px);
  color: var(--text-60);
  margin-bottom: 18px;
}

.closing-website {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 11px 24px;
  border-radius: 6px;
  background: linear-gradient(135deg, var(--primary) 0%, #7c3aed 100%);
  color: #fff;
  font-family: var(--font-heading);
  font-size: clamp(16px, 2.6vw, 20px);
  font-weight: 700;
  text-decoration: none;
  margin-bottom: 18px;
  box-shadow: 0 0 20px var(--primary-dim);
}
.closing-website svg { width: 16px; height: 16px; }

.closing-cta {
  font-family: var(--font-mono);
  font-size: clamp(13px, 2vw, 16px);
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
        <div class="closing-card">
          <div class="slide-number">N/N</div>
          <div class="closing-avatar">
            <img src="../images/about-pedro.png" alt="Pedro Marins" />
          </div>
          <div class="closing-name">Pedro Marins</div>
          <div class="closing-handle">@pedromarins.ai</div>
          <div class="closing-website">
            <svg><!-- link icon --></svg>
            marinssolutions.com
          </div>
          <p class="closing-cta">Siga para mais conteudo como esse</p>
        </div>
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
.closing-card     { width: min(100%, 720px) !important; padding: 48px 54px 56px !important; }
.closing-avatar   { width: 168px !important; height: 168px !important; }
.closing-name     { font-size: clamp(36px, 5.5vw, 64px) !important; }
.closing-handle   { font-size: clamp(18px, 2.4vw, 30px) !important; }
.closing-website  { font-size: clamp(18px, 2.5vw, 30px) !important; padding: 18px 42px !important; }
.closing-cta      { font-size: clamp(15px, 2.2vw, 26px) !important; }
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
