import { z } from "zod";

/**
 * The blog post document (`blog_posts.content`, schema `blog.v2`; AE-0423,
 * ADR-0025). Mirrors the backend `BlogDocument`. The public API serves a
 * projection of it (no quality, image prompt/model), so editor-only keys are
 * optional here. There is no v1 shape: anything without `schema: "blog.v2"`
 * is rejected by `parseBlogContent`.
 */

export const BLOG_SCHEMA_V2 = "blog.v2" as const;

export const blogImageSchema = z.object({
  url: z.string().min(1),
  alt: z.string().trim().min(1),
  caption: z.string().nullable().optional(),
  source: z.string().optional(),
  created_at: z.string().nullable().optional(),
  prompt: z.string().nullable().optional(),
  model: z.string().nullable().optional(),
});

export const blogSectionSchema = z.object({
  id: z.string().min(1),
  heading: z.string().nullable(),
  body_md: z.string(),
  image: blogImageSchema.nullable(),
});

export const blogLanguageDocumentSchema = z.object({
  schema: z.literal(BLOG_SCHEMA_V2),
  cover: blogImageSchema.nullable(),
  sections: z.array(blogSectionSchema),
  quality: z.unknown().optional(),
});

export const blogDocumentSchema = blogLanguageDocumentSchema.extend({
  translations: z.record(z.string(), blogLanguageDocumentSchema).default({}),
});

/** Editor-only voice/repetition scores (`content.quality`, AE-0425 writes). */
export const blogQualitySchema = z.object({
  voice_score: z.number(),
  voice_breakdown: z
    .record(z.string(), z.union([z.number(), z.array(z.string())]))
    .default({}),
  rewrite_passes: z.number().optional(),
  checked_at: z.string().nullable().optional(),
});

export type BlogImage = z.infer<typeof blogImageSchema>;
export type BlogSection = z.infer<typeof blogSectionSchema>;
export type BlogLanguageDocument = z.infer<typeof blogLanguageDocumentSchema>;
export type BlogDocument = z.infer<typeof blogDocumentSchema>;
