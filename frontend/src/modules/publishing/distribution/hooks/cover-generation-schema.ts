import { z } from "zod";

/**
 * Response schemas of the Grok cover generations endpoint. Standalone (no
 * local imports) so the hook types can use them without an import cycle.
 */
export const GENERATION_STATUS = {
  PENDING: "pending",
  SUCCEEDED: "succeeded",
  FAILED: "failed",
} as const;

export const coverGenerationSchema = z.object({
  id: z.string(),
  status: z.enum([
    GENERATION_STATUS.PENDING,
    GENERATION_STATUS.SUCCEEDED,
    GENERATION_STATUS.FAILED,
  ]),
  error_code: z.string().nullable().optional(),
  error_detail: z.string().nullable().optional(),
  asset_id: z.string().nullable().optional(),
  created_at: z.string(),
  completed_at: z.string().nullable().optional(),
});

export const coverGenerationsSchema = z.object({
  carousel_used: z.number(),
  carousel_cap: z.number(),
  month_used: z.number(),
  month_cap: z.number(),
  carousel_attempts: z.number(),
  carousel_attempt_cap: z.number(),
  month_attempts: z.number(),
  month_attempt_cap: z.number(),
  generations: z.array(coverGenerationSchema),
});

export type CoverGeneration = z.infer<typeof coverGenerationSchema>;
export type CoverGenerations = z.infer<typeof coverGenerationsSchema>;
