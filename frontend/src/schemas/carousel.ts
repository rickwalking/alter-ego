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
  rendered_slides_pt: z.array(z.string()).nullable().optional(),
  rendered_slides_en: z.array(z.string()).nullable().optional(),
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

export const carouselProjectResponseSchema = z.object({
  id: z.string(),
  topic: z.string(),
  audience: z.string(),
  niche: z.string(),
  language: z.string(),
  title: z.string().nullable(),
  subtitle: z.string().nullable(),
  title_en: z.string().nullable().optional(),
  subtitle_en: z.string().nullable().optional(),
  theme: z.string(),
  status: z.string(),
  image_model: z.string().optional(),
  image_style: z.string().optional(),
  custom_visual_details: z.string().nullable().optional(),
  primary_color: z.string().nullable(),
  accent_color: z.string().nullable(),
  background_color: z.string().nullable(),
  is_public: z.boolean().optional(),
  current_phase: z.string().nullable().optional(),
  phase_status: z.string().nullable().optional(),
  needs_republish_since: z.string().nullable().optional(),
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
  content_mode: z.enum(["news_analysis", "pov", "pov_news"]).optional(),
  pov_thesis: z.string().nullable().optional(),
  pov_personal_proof: z.string().nullable().optional(),
  pov_format: z.string().nullable().optional(),
  slide_count: z.number().nullable().optional(),
  cta_goal: z.string().nullable().optional(),
  hook_text: z.string().nullable().optional(),
  hook_asset_id: z.string().nullable().optional(),
  persona_id: z.string().nullable().optional(),
  rubric_id: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const carouselProjectListResponseSchema = z.object({
  items: z.array(carouselProjectResponseSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export const carouselPublicSlideSchema = z.object({
  slide_number: z.number(),
  heading: z.string().nullable(),
  image_url: z.string(),
});

export const carouselPublicResponseSchema = z.object({
  id: z.string(),
  topic: z.string().nullable().optional(),
  title: z.string().nullable(),
  title_en: z.string().nullable(),
  subtitle: z.string().nullable(),
  subtitle_en: z.string().nullable(),
  language: z.string(),
  created_at: z.string(),
  slide_count: z.number(),
  available_languages: z.array(z.string()),
  slides_by_language: z.record(z.string(), z.array(carouselPublicSlideSchema)),
  cover_url: z.string().nullable(),
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
export const SUPPORTED_IMAGE_COMBOS: readonly (readonly [string, string])[] = [
  ["openai", "comic_neon"],
  ["openai", "cinematic"],
  ["openai", "hyperreal"],
  ["openai", "neo_anime"],
  ["openai", "flat_editorial"],
  ["openai", "pov_editorial"],
];

export const carouselCreateRequestSchema = z
  .object({
    topic: z.string().min(1).max(500),
    audience: z.string().min(1).max(500),
    niche: z.string().min(1).max(200),
    /** Root key, "auto" or a custom-palette UUID; matches the backend varchar(64) so custom-palette references validate. */
    theme: z.string().max(64).default("auto"),
    image_model: z.enum(["gemini", "openai"]).default("openai"),
    image_style: z
      .enum([
        "comic_neon",
        "cinematic",
        "hyperreal",
        "neo_anime",
        "flat_editorial",
        "pov_editorial",
      ])
      .default("flat_editorial"),
    strategy: z.string().max(50).optional(),
    custom_visual_details: z.string().max(500).nullable().optional(),
    /** Content mode and the "Ponto de Vista" inputs (ADR-0021). */
    content_mode: z.enum(["news_analysis", "pov", "pov_news"]).optional(),
    pov_thesis: z.string().trim().min(1).max(280).optional(),
    pov_personal_proof: z.string().max(500).nullable().optional(),
    pov_format: z
      .enum(["opiniao", "como_eu_faco", "erros_e_mitos", "comparacao"])
      .optional(),
    slide_count: z.number().int().min(7).max(10).optional(),
    cta_goal: z.enum(["follow", "send", "comment"]).optional(),
    persona_id: z.string().uuid().nullable().optional(),
    rubric_id: z.string().uuid().nullable().optional(),
    /** Required by the API when content_mode is "pov" or "pov_news". */
    hook_asset_id: z.string().uuid().optional(),
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

/**
 * One slide-edit violation addressed to its form field
 * (``CarouselSlideEditResponse.field_violations``).
 */
export const slideFieldViolationSchema = z.object({
  code: z.string(),
  message: z.string(),
  severity: z.enum(["blocker", "warning"]),
  slide_index: z.number().nullable().optional(),
  locale: z.string().nullable().optional(),
  field: z.string().nullable().optional(),
  item_list: z.string().nullable().optional(),
  item_index: z.number().nullable().optional(),
  item_field: z.string().nullable().optional(),
});

export type CarouselDesignResponse = z.infer<
  typeof carouselDesignResponseSchema
>;
export type CarouselProjectResponse = z.infer<
  typeof carouselProjectResponseSchema
>;
export type CarouselProjectListResponse = z.infer<
  typeof carouselProjectListResponseSchema
>;
export type CarouselPublicSlide = z.infer<typeof carouselPublicSlideSchema>;
export type CarouselPublicResponse = z.infer<
  typeof carouselPublicResponseSchema
>;
export type CarouselCreateRequest = z.infer<typeof carouselCreateRequestSchema>;
