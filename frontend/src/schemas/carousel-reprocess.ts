import { z } from "zod";

export const carouselReprocessCapabilitySchema = z.object({
  can_reprocess: z.boolean(),
  refusal_code: z.string().nullable(),
  stuck_kind: z.string().nullable(),
  run_id: z.string().nullable(),
  status: z.string().nullable(),
  last_phase: z.string().nullable(),
  last_error_code: z.string().nullable(),
  position: z.number().int().nullable(),
  eta_seconds: z.number().int().nullable(),
  lock_version: z.number().int().nullable(),
});

export const manualReprocessResponseSchema = z.object({
  outcome: z.enum(["queued", "existing"]),
  run_id: z.string(),
  status: z.string(),
  stuck_kind: z.string().nullable(),
  position: z.number().int().nullable(),
  eta_seconds: z.number().int().nullable(),
  lock_version: z.number().int().nullable(),
  worker_notified: z.boolean(),
  last_error_code: z.string().nullable(),
});

export type CarouselReprocessCapability = z.infer<
  typeof carouselReprocessCapabilitySchema
>;
export type ManualReprocessResponse = z.infer<
  typeof manualReprocessResponseSchema
>;
