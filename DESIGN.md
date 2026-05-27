# Design: Neon Shell — Alter-Ego Cyberpunk Design System

## Overview

A deliberately maximalist cyberpunk/Ghost in the Shell-inspired design system for Pedro Marins' personal AI knowledge portal. Dark-drenched, neon-articulated, with CRT scanlines and holographic grid textures.

## Color

### Base palette

All colors are specified in OKLCH for perceptual uniformity.

| Name | Hex | OKLCH | Role |
|------|-----|-------|------|
| Cyan | `#00d4ff` | oklch(0.80 0.18 210) | Primary neon — interactive elements, borders, grid |
| Magenta | `#ff2770` | oklch(0.60 0.28 350) | Secondary neon — highlights, emphasis, glitch |
| Amber | `#f59e0b` | oklch(0.78 0.16 80) | Alert accent — section highlights, carousel palette |
| Teal | `#0ac5a8` | oklch(0.72 0.16 175) | Terminal prompts, secondary success states |
| Purple | `#a855f7` | oklch(0.58 0.25 300) | Feature card accent, carousel palette |
| Red | `#ef4444` | oklch(0.58 0.25 25) | Security theme, carousel palette |

### Neutrals (tinted toward cyan)

| Name | Value | Role |
|------|-------|------|
| bg-deep | `#060a12` | Page background |
| bg-surface | `#0a0f1e` | Section backgrounds, terminal |
| bg-card | `#0d1324` | Card surfaces |
| bg-elevated | `#111a30` | Elevated surfaces, hover states |
| text | rgba(255,255,255,0.88) | Primary text |
| text-muted | rgba(255,255,255,0.55) | Secondary text |
| text-dim | rgba(255,255,255,0.30) | Placeholder, metadata |

Neutrals avoid `#000` and `#fff`. Every neutral is slightly cool-tinted (cyan undertone, chroma ~0.005).

### Color strategy: Drenched

The background IS the color — `#060a12` is the canvas, and neon accents are applied as light sources rather than surface fills. Cyan carries ~30% of the interactive surface. Magenta is reserved for emphasis (<10%). This is not "restrained with one accent" — the deep background itself is a deliberate choice that defines the brand.

### Carousel theme palettes (secondary system)

Five topic-aware color identities drawn from the backend carousel pipeline. Displayed as a preview grid on the landing page:

| Theme | Primary | Accent |
|-------|---------|--------|
| Cybersecurity | `#ef4444` | `#00d4ff` |
| AI Competition | `#3b82f6` | `#f59e0b` |
| Developer Skills | `#0ac5a8` | `#8b5cf6` |
| Source Code | `#a855f7` | `#f97316` |
| Social Engineering | `#f59e0b` | `#ef4444` |

## Typography

| Element | Font | Weight | Size (clamped) |
|---------|------|--------|----------------|
| Hero heading | Inter | 900 | clamp(40px, 6vw, 72px) |
| Section title | Inter | 800 | clamp(32px, 4vw, 48px) |
| Card heading | Inter | 700–800 | 18–24px |
| Body | Inter | 400 | 14–16px |
| Meta / small | Inter | 500 | 13px |
| Monospace | JetBrains Mono | 400–700 | 9–14px |
| Badge text | JetBrains Mono | 700 | 10–11px |

- Body line length capped at 65–75ch.
- Scale ratio between steps ≥1.25 (h1 → h2 → h3).
- No em dashes in copy.
- Monospace for all technical UI (badges, terminal, labels, section identifiers).
- All text containers use `overflow-wrap: break-word` and `word-break: break-word` to prevent overflow on long content.
- Below-fold images use `loading="lazy"` for deferred loading. Above-fold hero images load eagerly.

## Spacing & Layout

- Container max-width: 1200px.
- Section padding: 100px vertical (60px on mobile).
- Gap rhythm varies: 24px between grid items, 16px between sidebar items, 60px between hero columns.
- No nested cards. Cards are single-level surfaces.
- The grid background extends across the full viewport, fixed, with a 3D perspective rotation (60deg).
- Flex containers use `min-width: 0` to prevent overflow from flex children with long content.

## Signature Effects

### Scanline overlay
A fixed `::after` on `<body>`: repeating-linear-gradient at 2px intervals with 1.5% cyan opacity. The only screen-effect overlay in the system. Never removed.

### Grid background
Fixed full-viewport grid: 1px lines at 3% cyan, 60px cells, rotated 60deg in 3D perspective, with a slow infinite scroll animation (20s). Parallax offset on scroll via JS.

### Terminal component
MacOS-style window chrome with colored dots + title bar. Inner text uses typewriter animation (staggered fade-in + translateX). Cyan prompt character, teal success indicators, magenta alert symbol. Blinking cursor. Represents the "system" character of the brand.

### Glitch text
CSS-only glitch on hero heading: `::before` (magenta) and `::after` (cyan) pseudo-elements offset by ±2px with alternating animation. Applied via `.glitch` class with `data-text` attribute.

### Neon glow rings
Radial gradients behind the terminal: 400px and 300px circles at 4% and 3% opacity, slowly pulsing (4s ease-in-out). Cyan and magenta alternated.

## Components

### Buttons
- **Primary**: Cyan gradient (#00d4ff → #0090b0), dark text, cyan box-shadow glow. Hover: lift 2px, intensify glow.
- **Ghost**: Transparent, cyan border at 30%. Hover: cyan-dim background fill, lift 2px.

### Feature cards
- **Primary (full-width)**: 2-column grid with visual panel + body panel. Cyan border at 12%. Hover/active: intensify border to 25%, add glow.
- **Secondary**: Single column, dark card surface. Top-border accent line (2px) that appears on hover/active. Lift 4px on hover/active. Teal and purple assigned per card.

### Theme blocks
Grid of 5 swatches, 2px gap between them. Each has its own background color and accent palette shown as color dots. Scale-on-hover and scale-on-active with z-index bump.

### Posts grid
Asymmetric layout: featured post (1.3fr) with hero image + sidebar (0.7fr) with stacked items. Never identical cards. Featured post lifts 4px on hover/active with intensified border and glow. Sidebar items shift to elevated background on hover/active.

### Stats bar
Full-width strip with 3 centered stats. Solid cyan numbers with text-shadow glow. Top and bottom cyan borders.

## Motion

- No CSS layout properties animated.
- Ease-out-quart curves for all transitions.
- Fade-in on scroll via IntersectionObserver: translateY(24px) → 0, 0.6s duration, staggered delays (0.1–0.3s).
- Terminal type animation: 0.6s per line, staggered by 0.6s, translateX(-8px) → 0.
- Grid drift: 20s linear infinite.
- Particle float: 6–12s random duration, ease-out.
- Ring pulse: 4s ease-in-out.
- Glitch offset: 3s linear alternate-reverse.
- **Motion sensitivity**: All animations guarded by `@media (prefers-reduced-motion: reduce)` that sets `animation-duration: 0.01ms !important` and `animation-iteration-count: 1 !important` on all elements.

## Responsive behavior

| Breakpoint | Changes |
|-----------|---------|
| ≤900px | Hero → single column (visual on top), features → 1-col, posts → 1-col, stats → 1-col, theme grid → 3-col |
| ≤600px | Theme grid → 2-col, condensed header nav, reduced padding everywhere |

## Accessibility

- **Focus-visible**: 2px solid cyan outline with 2px offset on all interactive elements. Applied via `:focus-visible`.
- **Selection**: Cyan-tinted background (`rgba(0,212,255,0.3)`) with near-white text for legibility on dark canvas. Applied via `::selection`.
- **Custom scrollbar**: 8px wide. Transparent track. Cyan-tinted thumb at 15% opacity (25% on hover), 4px border-radius. Applied via `::-webkit-scrollbar`.
- **Motion sensitivity**: All animations and transitions guarded by a `@media (prefers-reduced-motion: reduce)` rule that nullifies durations and iterations.
- **Touch feedback**: All hover-based interactions (translateY lifts, scale transforms, border highlights) duplicated under `:active` for mobile/touch users.
- **Broken image fallback**: Inline `<img>` elements use `onerror="this.style.display='none'"` to avoid broken icon artifacts.
- **Images**: All below-fold images use `loading="lazy"`. Decorative elements (grid, particles, scanlines) use `aria-hidden="true"`.
- **Color contrast**: All text maintains ≥4.5:1 ratio against `#060a12` background. Hero body text at `rgba(255,255,255,0.55)` on `#060a12` = ~6.8:1.
