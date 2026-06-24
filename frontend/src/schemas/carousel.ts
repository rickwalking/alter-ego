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

export const carouselBlogImageMapEntrySchema = z.object({
  slide_number: z.number(),
  heading: z.string(),
  alt: z.string(),
});

export const carouselDesignImagesSchema = z.object({
  hero: z.string(),
  slides: z.array(z.string()),
  rendered_slides_pt: z.array(z.string()).nullable().optional(),
  rendered_slides_en: z.array(z.string()).nullable().optional(),
  blog_image_map: z
    .array(carouselBlogImageMapEntrySchema)
    .nullable()
    .optional(),
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

// Same shape as the i18n response plus a design block (AE-0154 dedup).
export const carouselBlogWithDesignResponseSchema =
  carouselBlogI18nResponseSchema.extend({
    design: carouselDesignResponseSchema,
  });

export const carouselProjectResponseSchema = z.object({
  id: z.string(),
  topic: z.string(),
  audience: z.string(),
  niche: z.string(),
  title: z.string().nullable(),
  subtitle: z.string().nullable(),
  title_en: z.string().nullable().optional(),
  subtitle_en: z.string().nullable().optional(),
  theme: z.string(),
  status: z.string(),
  image_model: z.string().optional(),
  image_style: z.string().optional(),
  primary_color: z.string().nullable(),
  accent_color: z.string().nullable(),
  background_color: z.string().nullable(),
  is_public: z.boolean().optional(),
  current_phase: z.string().nullable().optional(),
  phase_status: z.string().nullable().optional(),
  error_message: z.string().nullable().optional(),
  output_dir: z.string().nullable().optional(),
  research_sources: z.array(z.unknown()).optional(),
  slides: z.array(z.unknown()).optional(),
  blog_markdown: z.string().nullable(),
  blog_translations: z.record(z.string(), z.string()).nullable().optional(),
  caption: z.string().nullable(),
  linkedin_post_pt: z.string().nullable().optional(),
  linkedin_post_en: z.string().nullable().optional(),
  pdf_path: z.string().nullable().optional(),
  pdf_path_en: z.string().nullable().optional(),
  design_tokens: z.unknown().nullable().optional(),
  creator_name: z.string().nullable().optional(),
  creator_handle: z.string().nullable().optional(),
  creator_avatar_url: z.string().nullable().optional(),
  template_version: z.string().nullable().optional(),
  slide_layout_strategy: z.string().nullable().optional(),
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
  slide_number: z.number(),
  slide_type: z.string(),
  heading: z.string(),
  body: z.string(),
  image_path: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Only these (model, style) tuples are wired in the backend registry.
 * Anything else is rejected by the API with 422 before the pipeline runs.
 */
export const SUPPORTED_IMAGE_COMBOS: ReadonlyArray<readonly [string, string]> =
  [
    ["gemini", "comic_neon"],
    ["openai", "cinematic"],
    ["openai", "hyperreal"],
    ["openai", "neo_anime"],
    ["openai", "flat_editorial"],
  ];

export const carouselCreateRequestSchema = z
  .object({
    topic: z.string().min(1).max(500),
    audience: z.string().min(1).max(500),
    niche: z.string().min(1).max(200),
    // root key | "auto" | custom-palette UUID (36 chars). Matches the backend
    // varchar(64) widened in AE-0268 so custom-palette references validate.
    theme: z.string().max(64).default("auto"),
    image_model: z.enum(["gemini", "openai"]).default("openai"),
    image_style: z
      .enum([
        "comic_neon",
        "cinematic",
        "hyperreal",
        "neo_anime",
        "flat_editorial",
      ])
      .default("neo_anime"),
    strategy: z.string().max(50).optional(),
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

export const carouselPhaseProgressSlideSchema = z.object({
  number: z.number(),
  status: z.enum(["pending", "in_flight", "done", "failed"]),
  style: z.string().optional(),
  scene: z.string().optional(),
});

export const carouselPhaseProgressSchema = z.object({
  phase: z.string(),
  label: z.string(),
  current: z.number().optional(),
  total: z.number().optional(),
  detail: z.string().optional(),
  slides: z.array(carouselPhaseProgressSlideSchema).optional(),
});

export type CarouselPhaseProgress = z.infer<typeof carouselPhaseProgressSchema>;

export type CarouselBlogImageMapEntry = z.infer<
  typeof carouselBlogImageMapEntrySchema
>;
export type CarouselDesignResponse = z.infer<
  typeof carouselDesignResponseSchema
>;
export type CarouselBlogI18nResponse = z.infer<
  typeof carouselBlogI18nResponseSchema
>;
export type CarouselBlogWithDesignResponse = z.infer<
  typeof carouselBlogWithDesignResponseSchema
>;
export type CarouselProjectResponse = z.infer<
  typeof carouselProjectResponseSchema
>;
export type CarouselProjectListResponse = z.infer<
  typeof carouselProjectListResponseSchema
>;
export type CarouselSlideResponse = z.infer<typeof carouselSlideResponseSchema>;
export type CarouselCreateRequest = z.infer<typeof carouselCreateRequestSchema>;
