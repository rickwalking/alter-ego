import type { CarouselDesignResponse } from "@/schemas/carousel";

export const BLOG_BADGES = {
  AI_ML: "AI/ML",
  CYBERSECURITY: "Cybersecurity",
  DEV_TOOLS: "Dev Tools",
  OPEN_SOURCE: "Open Source",
} as const;

/** Theme key to design token mapping, populated from API. */
export type BlogThemeKey = string;

/** CSS custom property names for blog theming. */
export const BLOG_CSS_VARS = {
  PRIMARY: "--blog-primary",
  ACCENT: "--blog-accent",
  BG: "--blog-bg",
  TEXT: "--blog-text",
  TEXT_MUTED: "--blog-text-muted",
  TEXT_DIM: "--blog-text-dim",
  BORDER: "--blog-border",
  GLOW: "--blog-glow",
  FONT_HEADING: "--blog-font-heading",
  FONT_BODY: "--blog-font-body",
  FONT_BADGE: "--blog-font-badge",
} as const;

/** Fallback theme used when design tokens are not yet loaded. */
export const FALLBACK_DESIGN_TOKENS: CarouselDesignResponse = {
  colors: {
    primary: "#3b82f6",
    accent: "#f59e0b",
    bg: "#0a0e17",
    text: "#ffffff",
    text_muted: "rgba(255,255,255,0.63)",
    text_dim: "rgba(255,255,255,0.48)",
    border: "#3b82f633",
    glow: "#3b82f60D",
  },
  typography: {
    font_family_heading: "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
    font_family_body: "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
    font_family_badge: "'Courier New', monospace",
  },
  images: {
    hero: "",
    slides: [],
  },
  layout: {
    badge_label: "AI/ML",
    swipe_text: "Deslize \u2192",
    progress_segments: 7,
  },
  theme_name: "ai_competition",
};

/** Convert design tokens to CSS custom properties style object. */
export function designTokensToCssVars(
  design: CarouselDesignResponse,
): Record<string, string> {
  return {
    [BLOG_CSS_VARS.PRIMARY]: design.colors.primary,
    [BLOG_CSS_VARS.ACCENT]: design.colors.accent,
    [BLOG_CSS_VARS.BG]: design.colors.bg,
    [BLOG_CSS_VARS.TEXT]: design.colors.text,
    [BLOG_CSS_VARS.TEXT_MUTED]: design.colors.text_muted,
    [BLOG_CSS_VARS.TEXT_DIM]: design.colors.text_dim,
    [BLOG_CSS_VARS.BORDER]: design.colors.border,
    [BLOG_CSS_VARS.GLOW]: design.colors.glow,
    [BLOG_CSS_VARS.FONT_HEADING]: design.typography.font_family_heading,
    [BLOG_CSS_VARS.FONT_BODY]: design.typography.font_family_body,
    [BLOG_CSS_VARS.FONT_BADGE]: design.typography.font_family_badge,
  };
}

export const ROUTE_PATHS = {
  BLOG: "/blog",
  HOME: "/",
} as const;

/**
 * Carousel slide intrinsic dimensions (px). The carousel design template
 * renders every slide at a fixed 1080x1350 (see backend
 * `agents/prompts/_shared/variables.yaml`), so embedded slide images in blog
 * posts have a known aspect ratio for next/image responsive sizing.
 */
export const CAROUSEL_SLIDE_WIDTH = 1080;
export const CAROUSEL_SLIDE_HEIGHT = 1350;
