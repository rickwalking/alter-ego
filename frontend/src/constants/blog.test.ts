import { describe, it, expect } from "vitest";
import {
  BLOG_BADGES,
  BLOG_CSS_VARS,
  FALLBACK_DESIGN_TOKENS,
  designTokensToCssVars,
  ROUTE_PATHS,
} from "@/constants/blog";
import { carouselDesignResponseSchema } from "@/schemas/carousel";

const MOCK_DESIGN = {
  colors: {
    primary: "#ef4444",
    accent: "#00d4ff",
    bg: "#0a0e17",
    text: "#ffffff",
    text_muted: "rgba(255,255,255,0.63)",
    text_dim: "rgba(255,255,255,0.48)",
    border: "#ef444433",
    glow: "#ef44440D",
  },
  typography: {
    font_family_heading: "'Inter', sans-serif",
    font_family_body: "'Inter', sans-serif",
    font_family_badge: "'JetBrains Mono', monospace",
  },
  images: {
    hero: "/api/carousels/1/images/hero",
    slides: ["/api/carousels/1/images/slide_1.jpg"],
  },
  layout: {
    badge_label: "Cybersecurity",
    swipe_text: "Swipe →",
    progress_segments: 10,
  },
  theme_name: "cybersecurity",
};

describe("BLOG_BADGES", () => {
  it("defines expected badge labels", () => {
    expect(BLOG_BADGES.AI_ML).toBe("AI/ML");
    expect(BLOG_BADGES.CYBERSECURITY).toBe("Cybersecurity");
    expect(BLOG_BADGES.DEV_TOOLS).toBe("Dev Tools");
    expect(BLOG_BADGES.OPEN_SOURCE).toBe("Open Source");
  });
});

describe("BLOG_CSS_VARS", () => {
  // Scenario: Blog CSS variables have correct property names
  it("maps PRIMARY to --blog-primary", () => {
    expect(BLOG_CSS_VARS.PRIMARY).toBe("--blog-primary");
  });

  it("maps ACCENT to --blog-accent", () => {
    expect(BLOG_CSS_VARS.ACCENT).toBe("--blog-accent");
  });

  it("maps BG to --blog-bg", () => {
    expect(BLOG_CSS_VARS.BG).toBe("--blog-bg");
  });

  it("maps TEXT to --blog-text", () => {
    expect(BLOG_CSS_VARS.TEXT).toBe("--blog-text");
  });

  it("maps TEXT_MUTED to --blog-text-muted", () => {
    expect(BLOG_CSS_VARS.TEXT_MUTED).toBe("--blog-text-muted");
  });

  it("maps TEXT_DIM to --blog-text-dim", () => {
    expect(BLOG_CSS_VARS.TEXT_DIM).toBe("--blog-text-dim");
  });

  it("maps BORDER to --blog-border", () => {
    expect(BLOG_CSS_VARS.BORDER).toBe("--blog-border");
  });

  it("maps GLOW to --blog-glow", () => {
    expect(BLOG_CSS_VARS.GLOW).toBe("--blog-glow");
  });

  it("maps FONT_HEADING to --blog-font-heading", () => {
    expect(BLOG_CSS_VARS.FONT_HEADING).toBe("--blog-font-heading");
  });

  it("maps FONT_BODY to --blog-font-body", () => {
    expect(BLOG_CSS_VARS.FONT_BODY).toBe("--blog-font-body");
  });

  it("maps FONT_BADGE to --blog-font-badge", () => {
    expect(BLOG_CSS_VARS.FONT_BADGE).toBe("--blog-font-badge");
  });
});

describe("FALLBACK_DESIGN_TOKENS", () => {
  // Scenario: Fallback design tokens match schema
  it("validates against carouselDesignResponseSchema", () => {
    const result = carouselDesignResponseSchema.safeParse(FALLBACK_DESIGN_TOKENS);
    expect(result.success).toBe(true);
  });

  it("has primary color as blue", () => {
    expect(FALLBACK_DESIGN_TOKENS.colors.primary).toBe("#3b82f6");
  });

  it("has dark background color", () => {
    expect(FALLBACK_DESIGN_TOKENS.colors.bg).toBe("#0a0e17");
  });

  it("has empty hero image by default", () => {
    expect(FALLBACK_DESIGN_TOKENS.images.hero).toBe("");
  });

  it("has empty slides array by default", () => {
    expect(FALLBACK_DESIGN_TOKENS.images.slides).toEqual([]);
  });

  it("has theme_name 'ai_competition'", () => {
    expect(FALLBACK_DESIGN_TOKENS.theme_name).toBe("ai_competition");
  });
});

describe("designTokensToCssVars", () => {
  // Scenario: Design tokens convert to CSS custom properties
  it("returns a flat Record<string, string>", () => {
    const result = designTokensToCssVars(MOCK_DESIGN);
    expect(typeof result).toBe("object");
    expect(Object.values(result).every((v) => typeof v === "string")).toBe(true);
  });

  it("maps each color field to the corresponding CSS variable", () => {
    const result = designTokensToCssVars(MOCK_DESIGN);

    expect(result[BLOG_CSS_VARS.PRIMARY]).toBe(MOCK_DESIGN.colors.primary);
    expect(result[BLOG_CSS_VARS.ACCENT]).toBe(MOCK_DESIGN.colors.accent);
    expect(result[BLOG_CSS_VARS.BG]).toBe(MOCK_DESIGN.colors.bg);
    expect(result[BLOG_CSS_VARS.TEXT]).toBe(MOCK_DESIGN.colors.text);
    expect(result[BLOG_CSS_VARS.TEXT_MUTED]).toBe(MOCK_DESIGN.colors.text_muted);
    expect(result[BLOG_CSS_VARS.TEXT_DIM]).toBe(MOCK_DESIGN.colors.text_dim);
    expect(result[BLOG_CSS_VARS.BORDER]).toBe(MOCK_DESIGN.colors.border);
    expect(result[BLOG_CSS_VARS.GLOW]).toBe(MOCK_DESIGN.colors.glow);
  });

  it("maps each typography field to the corresponding CSS variable", () => {
    const result = designTokensToCssVars(MOCK_DESIGN);

    expect(result[BLOG_CSS_VARS.FONT_HEADING]).toBe(MOCK_DESIGN.typography.font_family_heading);
    expect(result[BLOG_CSS_VARS.FONT_BODY]).toBe(MOCK_DESIGN.typography.font_family_body);
    expect(result[BLOG_CSS_VARS.FONT_BADGE]).toBe(MOCK_DESIGN.typography.font_family_badge);
  });

  it("produces exactly 11 CSS custom properties", () => {
    const result = designTokensToCssVars(MOCK_DESIGN);
    expect(Object.keys(result)).toHaveLength(11);
  });

  it("works with FALLBACK_DESIGN_TOKENS", () => {
    const result = designTokensToCssVars(FALLBACK_DESIGN_TOKENS);
    expect(result[BLOG_CSS_VARS.PRIMARY]).toBe("#3b82f6");
    expect(result[BLOG_CSS_VARS.BG]).toBe("#0a0e17");
  });
});

describe("ROUTE_PATHS", () => {
  it("defines BLOG as /blog", () => {
    expect(ROUTE_PATHS.BLOG).toBe("/blog");
  });

  it("defines HOME as /", () => {
    expect(ROUTE_PATHS.HOME).toBe("/");
  });
});
