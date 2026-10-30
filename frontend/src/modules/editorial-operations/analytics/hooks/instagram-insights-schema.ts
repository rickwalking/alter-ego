import { z } from "zod";

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

export const instagramConnectorSchema = z.object({
  channel: z.string(),
  configured: z.boolean(),
  last_sync_at: z.string().nullable(),
  stale: z.boolean(),
  error: z.string().nullable(),
});

export const instagramInsightsSchema = z.object({
  items: z.array(instagramPostInsightsSchema),
  follows_total: z.number().int().nullable(),
  follows_per_post: z.number().nullable(),
  shares_per_100_views: z.number().nullable(),
  configured: z.boolean(),
  connector: instagramConnectorSchema,
});

export type InstagramPostInsights = z.infer<typeof instagramPostInsightsSchema>;
export type InstagramConnector = z.infer<typeof instagramConnectorSchema>;
export type InstagramInsights = z.infer<typeof instagramInsightsSchema>;
