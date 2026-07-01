import { z } from "zod";

/**
 * Lean public blog-post payloads (AE-0297, ADR-0013). Mirrors the backend
 * allow-list schemas — internal/editorial fields never appear here.
 */

export const publicBlogPostSummarySchema = z.object({
  id: z.string(),
  slug: z.string(),
  title: z.string(),
  excerpt: z.string().nullable().optional(),
  featured_image_url: z.string().nullable().optional(),
  published_at: z.string().nullable().optional(),
  meta_title: z.string().nullable().optional(),
  meta_description: z.string().nullable().optional(),
  keywords: z.array(z.string()),
  canonical_url: z.string().nullable().optional(),
  origin: z.string(),
  project_id: z.string().nullable().optional(),
});

export const publicBlogPostResponseSchema = publicBlogPostSummarySchema.extend({
  content: z.record(z.string(), z.unknown()),
});

export const publicBlogPostListResponseSchema = z.object({
  items: z.array(publicBlogPostSummarySchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export type PublicBlogPostSummary = z.infer<typeof publicBlogPostSummarySchema>;
export type PublicBlogPostResponse = z.infer<
  typeof publicBlogPostResponseSchema
>;
export type PublicBlogPostListResponse = z.infer<
  typeof publicBlogPostListResponseSchema
>;
