# AE-0265 — light-theme-aware slide text composition

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: backend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: feat/carousel-palettes-light-editorial
Kanban Card: TBD
Created: 2026-06-22
Updated: 2026-06-22

## Goal

Make the carousel slide **text composition** light-theme-aware so the light
palettes (risograph, paper_editorial, clinical_mint) are postable: dark ink text
on a light background with a light scrim, WCAG body contrast ≥ 4.5:1 — instead of
the current white-text-on-light (unreadable).

## Problem (from AE-0264 live validation)

`carousel_template/css/base.py` hardcodes `--text: #ffffff` (+ white `--text-60/55/48`)
and the slide scrims are hardcoded dark (`rgba(10,12,20,…)` in `slide_styles_shell.py`,
`rgba(6,10,18,…)` in `slide_styles_closing.py`). On a light palette the artwork renders
correctly (AE-0264 fix) but the overlaid heading/body/structured-item text is white on
a light ground → near-invisible.

## Scope

- New `carousel_template/theme_mode.py`: WCAG relative luminance →
  `is_light_background(bg)` + `surface_css_vars(theme)` returning the `:root`
  values (`--text*`, `--scrim-*`, `--card-bg-*`, body bg) for light vs dark.
- `css/base.py`: build `:root` text + scrim + card vars from `surface_css_vars`;
  body bg/color follows the mode.
- `css/slide_styles_shell.py` + `css/slide_styles_closing.py`: replace hardcoded
  dark scrim/card rgba with the new `var(--scrim-*)` / `var(--card-bg-*)`.
- Dark palettes render **byte-identical** to today (mode=dark returns current values).

## Non-Goals

- No new palettes/presets (AE-0264). No image-strategy change. No per-palette
  primary-as-accent contrast tuning (risograph's orange primary may still warrant
  a later pass) beyond the body-ink readability fix.

## Acceptance Criteria

- [ ] A light-background theme renders dark ink text (`--text` is dark) + a light
      scrim; a dark theme is unchanged (current white/dark values).
- [ ] Body text contrast ≥ 4.5:1 on the light palettes (asserted in a test).
- [ ] No hardcoded dark scrim rgba remains in shell/closing slide CSS (replaced by vars).
- [ ] `.feature` + tests; backend ruff/mypy/lint-imports green; full suites green.
- [ ] Re-generated light carousel (paper_editorial/flat_editorial) reads cleanly.

## Affected Areas

- Backend: `carousel_template/theme_mode.py` (new), `css/base.py`,
  `css/slide_styles_shell.py`, `css/slide_styles_closing.py`
- Tests: `tests/unit/application/test_carousel_template_theme_mode.py` (new) +
  `tests/features/carousel_design_refinement.feature`

## QA Checklist

- [ ] Security reviewed (pure CSS string generation, no input)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases (mid-luminance palette, missing keys)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-22

Created from the AE-0264 light-validation finding. Implementing the luminance-driven
surface tokens.

## Test Evidence

Pending.

## QA Report

Pending.

## Final Summary

Pending.
