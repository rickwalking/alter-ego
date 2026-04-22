import { z } from "zod";

export const carouselDesignColorsSchema = z.object({
  primary: z.string(),
  accent: z.string(),
  bg: z.string(),
  text: z.string(),
  text_muted: z.string(),
  text_dim: z.string(),
  border: z.string(),
  glow: z.string(),
});

export const carouselDesignTypographySchema = z.object({
  font_family_heading: z.string(),
  font_family_body: z.string(),
  font_family_badge: z.string(),
});

export const carouselDesignImagesSchema = z.object({
  hero: z.string(),
  slides: z.array(z.string()),
});

export const carouselDesignLayoutSchema = z.object({
  badge_label: z.string(),
  swipe_text: z.string(),
  progress_segments: z.number(),
});

export const carouselDesignResponseSchema = z.object({
  colors: carouselDesignColorsSchema,
  typography: carouselDesignTypographySchema,
  images: carouselDesignImagesSchema,
  layout: carouselDesignLayoutSchema,
  theme_name: z.string(),
});

export const carouselBlogI18nResponseSchema = z.object({
  markdown: z.string(),
  title: z.string(),
  subtitle: z.string().nullable(),
  language: z.string(),
  available_languages: z.array(z.string()),
});

export const carouselBlogWithDesignResponseSchema = z.object({
  markdown: z.string(),
  title: z.string(),
  subtitle: z.string().nullable(),
  language: z.string(),
  available_languages: z.array(z.string()),
  design: carouselDesignResponseSchema,
});

export const carouselProjectResponseSchema = z.object({
  id: z.string(),
  topic: z.string(),
  audience: z.string(),
  niche: z.string(),
  title: z.string().nullable(),
  subtitle: z.string().nullable(),
  theme: z.string(),
  status: z.string(),
  blog_markdown: z.string().nullable(),
  blog_translations: z.record(z.string(), z.string()).nullable().optional(),
  caption: z.string().nullable(),
  design_tokens: z.unknown().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const carouselProjectListResponseSchema = z.object({
  items: z.array(carouselProjectResponseSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export const carouselSlideResponseSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  slide_number: z.number(),
  slide_type: z.string(),
  heading: z.string(),
  body: z.string(),
  image_prompt: z.string().nullable(),
  created_at: z.string(),
});

/**
 * Only these (model, style) tuples are wired in the backend registry.
 * Anything else is rejected by the API with 422 before the pipeline runs.
 */
export const SUPPORTED_IMAGE_COMBOS: ReadonlyArray<readonly [string, string]> = [
  ["gemini", "comic_neon"],
  ["openai", "cinematic"],
  ["openai", "hyperreal"],
  ["openai", "neo_anime"],
];

export const carouselCreateRequestSchema = z
  .object({
    topic: z.string().min(1).max(500),
    audience: z.string().min(1).max(500),
    niche: z.string().min(1).max(200),
    theme: z.string().max(30).default("auto"),
    image_model: z.enum(["gemini", "openai"]).default("gemini"),
    image_style: z
      .enum(["comic_neon", "cinematic", "hyperreal", "neo_anime"])
      .default("comic_neon"),
  })
  .refine(
    (data) =>
      SUPPORTED_IMAGE_COMBOS.some(
        ([m, s]) => m === data.image_model && s === data.image_style,
      ),
    {
      message: "image_model + image_style combination is not supported",
      path: ["image_style"],
    },
  );

export const carouselStatusResponseSchema = z.object({
  id: z.string(),
  status: z.string(),
  error_message: z.string().nullable(),
  updated_at: z.string(),
});

export type CarouselDesignResponse = z.infer<typeof carouselDesignResponseSchema>;
export type CarouselBlogI18nResponse = z.infer<typeof carouselBlogI18nResponseSchema>;
export type CarouselBlogWithDesignResponse = z.infer<typeof carouselBlogWithDesignResponseSchema>;
export type CarouselProjectResponse = z.infer<typeof carouselProjectResponseSchema>;
export type CarouselProjectListResponse = z.infer<typeof carouselProjectListResponseSchema>;
export type CarouselSlideResponse = z.infer<typeof carouselSlideResponseSchema>;
export type CarouselCreateRequest = z.infer<typeof carouselCreateRequestSchema>;
export type CarouselStatusResponse = z.infer<typeof carouselStatusResponseSchema>;