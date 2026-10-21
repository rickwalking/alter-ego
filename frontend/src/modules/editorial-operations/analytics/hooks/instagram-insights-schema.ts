import { z } from "zod";

/**
 * `GET /api/instagram/insights`. A metric the Graph API did not
 * return is `null` and the UI shows "n/d" — never an estimate.
 */
const metric = z.number().int().nullable();

export const instagramPostInsightsSchema = z.object({
  media_id: z.string(),
  carousel_project_id: z.string().nullable(),
  permalink: z.string().nullable(),
  topic: z.string().nullable(),
  views: metric,
  reach: metric,
  saved: metric,
  shares: metric,
  follows: metric,
  profile_visits: metric,
  total_interactions: metric,
  shares_per_100_views: z.number().nullable(),
  fetched_at: z.string().nullable(),
  stale: z.boolean(),
});

export const instagramInsightsSchema = z.object({
  items: z.array(instagramPostInsightsSchema),
  follows_total: z.number().int().nullable(),
  follows_per_post: z.number().nullable(),
  shares_per_100_views: z.number().nullable(),
  configured: z.boolean(),
});

export type InstagramPostInsights = z.infer<typeof instagramPostInsightsSchema>;
export type InstagramInsights = z.infer<typeof instagramInsightsSchema>;
