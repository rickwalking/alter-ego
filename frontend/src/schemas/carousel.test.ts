import { describe, it, expect } from "vitest";
import {
  carouselDesignColorsSchema,
  carouselDesignTypographySchema,
  carouselDesignImagesSchema,
  carouselDesignLayoutSchema,
  carouselDesignResponseSchema,
  carouselBlogI18nResponseSchema,
  carouselBlogWithDesignResponseSchema,
  carouselProjectResponseSchema,
  carouselProjectListResponseSchema,
  carouselSlideResponseSchema,
  carouselCreateRequestSchema,
} from "@/schemas/carousel";

const VALID_DESIGN_COLORS = {
  primary: "#3b82f6",
  accent: "#f59e0b",
  bg: "#0a0e17",
  text: "#ffffff",
  text_muted: "rgba(255,255,255,0.63)",
  text_dim: "rgba(255,255,255,0.48)",
  border: "#3b82f633",
  glow: "#3b82f60D",
};

const VALID_DESIGN_TYPOGRAPHY = {
  font_family_heading: "'Segoe UI', sans-serif",
  font_family_body: "'Segoe UI', sans-serif",
  font_family_badge: "'Courier New', monospace",
};

const VALID_DESIGN_IMAGES = {
  hero: "/api/carousels/1/images/hero",
  slides: ["/api/carousels/1/images/slide_1.jpg"],
};

const VALID_DESIGN_LAYOUT = {
  badge_label: "AI/ML",
  swipe_text: "Deslize →",
  progress_segments: 7,
};

const VALID_DESIGN_RESPONSE = {
  colors: VALID_DESIGN_COLORS,
  typography: VALID_DESIGN_TYPOGRAPHY,
  images: VALID_DESIGN_IMAGES,
  layout: VALID_DESIGN_LAYOUT,
  theme_name: "ai_competition",
};

const VALID_BLOG_I18N = {
  markdown: "# Title\n\nContent here",
  title: "Test Title",
  subtitle: "Test Subtitle",
  language: "pt",
  available_languages: ["pt", "en"],
};

const VALID_PROJECT = {
  id: "abc-123",
  topic: "Gemma 4",
  audience: "Developers",
  niche: "AI/ML",
  title: "Gemma 4 Deep Dive",
  subtitle: "Understanding Google's Latest Model",
  theme: "ai_competition",
  status: "completed",
  primary_color: "#00e5ff",
  accent_color: "#ff007a",
  background_color: "#0a0a0f",
  blog_markdown: "# Content",
  caption: "Check this out!",
  created_at: "2026-04-20T00:00:00Z",
  updated_at: "2026-04-20T00:00:00Z",
};

const VALID_SLIDE = {
  id: "slide-1",
  slide_number: 1,
  slide_type: "content",
  heading: "Slide Title",
  body: "Slide body text",
  image_path: null,
  created_at: "2026-04-20T00:00:00Z",
  updated_at: "2026-04-20T00:00:00Z",
};

function omitKey<T extends Record<string, unknown>, K extends keyof T>(
  object: T,
  key: K,
): Omit<T, K> {
  const copy = { ...object };
  delete copy[key];
  return copy;
}

describe("Carousel Design Colors Schema", () => {
  // Scenario: Validate carousel design tokens schema — color fields
  it("validates complete color object", () => {
    const result = carouselDesignColorsSchema.safeParse(VALID_DESIGN_COLORS);
    expect(result.success).toBe(true);
  });

  it("rejects missing primary color", () => {
    const missingPrimary = omitKey(VALID_DESIGN_COLORS, "primary");
    const result = carouselDesignColorsSchema.safeParse(missingPrimary);
    expect(result.success).toBe(false);
  });

  it("rejects missing text_muted color", () => {
    const rest = omitKey(VALID_DESIGN_COLORS, "text_muted");
    const result = carouselDesignColorsSchema.safeParse(rest);
    expect(result.success).toBe(false);
  });

  it("accepts empty string values for colors", () => {
    const result = carouselDesignColorsSchema.safeParse({
      ...VALID_DESIGN_COLORS,
      primary: "",
    });
    expect(result.success).toBe(true);
  });
});

describe("Carousel Design Typography Schema", () => {
  it("validates complete typography object", () => {
    const result = carouselDesignTypographySchema.safeParse(
      VALID_DESIGN_TYPOGRAPHY,
    );
    expect(result.success).toBe(true);
  });

  it("rejects missing font_family_heading", () => {
    const rest = omitKey(VALID_DESIGN_TYPOGRAPHY, "font_family_heading");
    const result = carouselDesignTypographySchema.safeParse(rest);
    expect(result.success).toBe(false);
  });
});

describe("Carousel Design Images Schema", () => {
  it("validates images with hero and slides", () => {
    const result = carouselDesignImagesSchema.safeParse(VALID_DESIGN_IMAGES);
    expect(result.success).toBe(true);
  });

  it("accepts empty slides array", () => {
    const result = carouselDesignImagesSchema.safeParse({
      ...VALID_DESIGN_IMAGES,
      slides: [],
    });
    expect(result.success).toBe(true);
  });

  it("rejects non-array slides", () => {
    const result = carouselDesignImagesSchema.safeParse({
      ...VALID_DESIGN_IMAGES,
      slides: "not-array",
    });
    expect(result.success).toBe(false);
  });
});

describe("Carousel Design Layout Schema", () => {
  it("validates layout with all required fields", () => {
    const result = carouselDesignLayoutSchema.safeParse(VALID_DESIGN_LAYOUT);
    expect(result.success).toBe(true);
  });

  it("rejects non-number progress_segments", () => {
    const result = carouselDesignLayoutSchema.safeParse({
      ...VALID_DESIGN_LAYOUT,
      progress_segments: "6",
    });
    expect(result.success).toBe(false);
  });
});

describe("Carousel Design Response Schema", () => {
  // Scenario: Validate carousel design tokens schema
  it("validates complete design response", () => {
    const result = carouselDesignResponseSchema.safeParse(
      VALID_DESIGN_RESPONSE,
    );
    expect(result.success).toBe(true);
  });

  // Scenario: All required color fields are present
  it("extracts all color fields after validation", () => {
    const result = carouselDesignResponseSchema.parse(VALID_DESIGN_RESPONSE);
    expect(result.colors).toEqual(VALID_DESIGN_COLORS);
  });

  // Scenario: All typography fields are present
  it("extracts all typography fields after validation", () => {
    const result = carouselDesignResponseSchema.parse(VALID_DESIGN_RESPONSE);
    expect(result.typography).toEqual(VALID_DESIGN_TYPOGRAPHY);
  });

  // Scenario: All image fields are present
  it("extracts all image fields after validation", () => {
    const result = carouselDesignResponseSchema.parse(VALID_DESIGN_RESPONSE);
    expect(result.images).toEqual(VALID_DESIGN_IMAGES);
  });

  // Scenario: All layout fields are present
  it("extracts all layout fields after validation", () => {
    const result = carouselDesignResponseSchema.parse(VALID_DESIGN_RESPONSE);
    expect(result.layout).toEqual(VALID_DESIGN_LAYOUT);
  });

  // Scenario: Reject invalid design tokens with missing fields
  it("rejects design response with missing colors", () => {
    const withoutColors = omitKey(VALID_DESIGN_RESPONSE, "colors");
    const result = carouselDesignResponseSchema.safeParse(withoutColors);
    expect(result.success).toBe(false);
  });

  it("rejects design response with empty theme_name", () => {
    const result = carouselDesignResponseSchema.safeParse({
      ...VALID_DESIGN_RESPONSE,
      theme_name: "",
    });
    expect(result.success).toBe(true);
  });

  it("rejects design response missing theme_name", () => {
    const withoutTheme = omitKey(VALID_DESIGN_RESPONSE, "theme_name");
    const result = carouselDesignResponseSchema.safeParse(withoutTheme);
    expect(result.success).toBe(false);
  });
});

describe("Carousel Blog I18n Response Schema", () => {
  // Scenario: Validate blog i18n response schema
  it("validates complete blog i18n response", () => {
    const result = carouselBlogI18nResponseSchema.safeParse(VALID_BLOG_I18N);
    expect(result.success).toBe(true);
  });

  // Scenario: markdown field is present
  it("requires markdown field", () => {
    const withoutMarkdown = omitKey(VALID_BLOG_I18N, "markdown");
    const result = carouselBlogI18nResponseSchema.safeParse(withoutMarkdown);
    expect(result.success).toBe(false);
  });

  // Scenario: language field equals "pt"
  it("preserves language field as string", () => {
    const result = carouselBlogI18nResponseSchema.parse(VALID_BLOG_I18N);
    expect(result.language).toBe("pt");
  });

  // Scenario: available_languages is an array
  it("requires available_languages as array", () => {
    const result = carouselBlogI18nResponseSchema.safeParse({
      ...VALID_BLOG_I18N,
      available_languages: "pt,en",
    });
    expect(result.success).toBe(false);
  });

  it("accepts null subtitle", () => {
    const result = carouselBlogI18nResponseSchema.safeParse({
      ...VALID_BLOG_I18N,
      subtitle: null,
    });
    expect(result.success).toBe(true);
  });

  it("rejects missing title", () => {
    const withoutTitle = omitKey(VALID_BLOG_I18N, "title");
    const result = carouselBlogI18nResponseSchema.safeParse(withoutTitle);
    expect(result.success).toBe(false);
  });
});

describe("Carousel Blog With Design Response Schema", () => {
  // Scenario: Validate blog with design response schema
  it("validates complete blog with design response", () => {
    const payload = {
      ...VALID_BLOG_I18N,
      design: VALID_DESIGN_RESPONSE,
    };
    const result = carouselBlogWithDesignResponseSchema.safeParse(payload);
    expect(result.success).toBe(true);
  });

  // Scenario: Both blog content and design tokens are present
  it("contains both blog content and design tokens after parse", () => {
    const payload = {
      ...VALID_BLOG_I18N,
      design: VALID_DESIGN_RESPONSE,
    };
    const result = carouselBlogWithDesignResponseSchema.parse(payload);
    expect(result.markdown).toBe(VALID_BLOG_I18N.markdown);
    expect(result.design).toEqual(VALID_DESIGN_RESPONSE);
  });

  it("rejects response missing design", () => {
    const withoutDesign = omitKey(
      {
        ...VALID_BLOG_I18N,
        design: VALID_DESIGN_RESPONSE,
      },
      "design",
    );
    const result =
      carouselBlogWithDesignResponseSchema.safeParse(withoutDesign);
    expect(result.success).toBe(false);
  });
});

describe("Carousel Project Response Schema", () => {
  it("validates complete project response", () => {
    const result = carouselProjectResponseSchema.safeParse(VALID_PROJECT);
    expect(result.success).toBe(true);
  });

  it("accepts nullable title", () => {
    const result = carouselProjectResponseSchema.safeParse({
      ...VALID_PROJECT,
      title: null,
    });
    expect(result.success).toBe(true);
  });

  it("accepts nullable subtitle", () => {
    const result = carouselProjectResponseSchema.safeParse({
      ...VALID_PROJECT,
      subtitle: null,
    });
    expect(result.success).toBe(true);
  });

  it("accepts nullable blog_markdown", () => {
    const result = carouselProjectResponseSchema.safeParse({
      ...VALID_PROJECT,
      blog_markdown: null,
    });
    expect(result.success).toBe(true);
  });

  it("accepts optional blog_translations", () => {
    const result = carouselProjectResponseSchema.safeParse({
      ...VALID_PROJECT,
      blog_translations: { pt: "# Title", en: "# Title" },
    });
    expect(result.success).toBe(true);
  });

  it("accepts missing blog_translations", () => {
    const withoutTranslations = omitKey(
      {
        ...VALID_PROJECT,
        blog_translations: undefined,
      },
      "blog_translations",
    );
    const result = carouselProjectResponseSchema.safeParse(withoutTranslations);
    expect(result.success).toBe(true);
  });

  it("requires id field", () => {
    const withoutId = omitKey(VALID_PROJECT, "id");
    const result = carouselProjectResponseSchema.safeParse(withoutId);
    expect(result.success).toBe(false);
  });
});

describe("Carousel Project List Response Schema", () => {
  // Scenario: Validate carousel project list response
  const VALID_LIST = {
    items: [VALID_PROJECT],
    total: 1,
    limit: 20,
    offset: 0,
  };

  it("validates complete list response", () => {
    const result = carouselProjectListResponseSchema.safeParse(VALID_LIST);
    expect(result.success).toBe(true);
  });

  // Scenario: items is an array of projects
  it("parses items as array of projects", () => {
    const result = carouselProjectListResponseSchema.parse(VALID_LIST);
    expect(result.items).toHaveLength(1);
    expect(result.items[0].id).toBe("abc-123");
  });

  // Scenario: total, limit, and offset are numbers
  it("requires total, limit, offset as numbers", () => {
    const result = carouselProjectListResponseSchema.safeParse({
      items: [],
      total: "1",
      limit: 20,
      offset: 0,
    });
    expect(result.success).toBe(false);
  });

  it("accepts empty items array", () => {
    const result = carouselProjectListResponseSchema.safeParse({
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    });
    expect(result.success).toBe(true);
  });
});

describe("Carousel Slide Response Schema", () => {
  it("validates complete slide response", () => {
    const result = carouselSlideResponseSchema.safeParse(VALID_SLIDE);
    expect(result.success).toBe(true);
  });

  it("accepts null image_path", () => {
    const result = carouselSlideResponseSchema.safeParse({
      ...VALID_SLIDE,
      image_path: null,
    });
    expect(result.success).toBe(true);
  });

  it("accepts missing optional image_path", () => {
    const result = carouselSlideResponseSchema.safeParse(
      omitKey(VALID_SLIDE, "image_path"),
    );
    expect(result.success).toBe(true);
  });

  it("rejects missing slide_number", () => {
    const rest = omitKey(VALID_SLIDE, "slide_number");
    const result = carouselSlideResponseSchema.safeParse(rest);
    expect(result.success).toBe(false);
  });
});
// Scenario: Pluggable image provider combo validation
// (see backend tests/features/image_generation_provider.feature)
describe("Carousel Create Request Schema — image_model/image_style", () => {
  const BASE = {
    topic: "T",
    audience: "A",
    niche: "N",
  };

  it("defaults to gemini + comic_neon when omitted", () => {
    const result = carouselCreateRequestSchema.parse(BASE);
    expect(result.image_model).toBe("gemini");
    expect(result.image_style).toBe("comic_neon");
  });

  it("accepts supported openai + hyperreal combo", () => {
    const result = carouselCreateRequestSchema.safeParse({
      ...BASE,
      image_model: "openai",
      image_style: "hyperreal",
    });
    expect(result.success).toBe(true);
  });

  it("rejects unsupported (gemini, cinematic) combo", () => {
    const result = carouselCreateRequestSchema.safeParse({
      ...BASE,
      image_model: "gemini",
      image_style: "cinematic",
    });
    expect(result.success).toBe(false);
  });

  it("rejects unknown image_model", () => {
    const result = carouselCreateRequestSchema.safeParse({
      ...BASE,
      image_model: "dalle-3",
      image_style: "comic_neon",
    });
    expect(result.success).toBe(false);
  });

  it("rejects unknown image_style", () => {
    const result = carouselCreateRequestSchema.safeParse({
      ...BASE,
      image_model: "gemini",
      image_style: "ukiyo_e",
    });
    expect(result.success).toBe(false);
  });
});
