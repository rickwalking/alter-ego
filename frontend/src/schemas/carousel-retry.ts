import { z } from "zod";

export const carouselRetryCapabilitySchema = z.object({
  can_retry: z.boolean(),
  retry_kind: z.string().nullable().optional(),
  refusal_code: z.string().nullable().optional(),
  lock_version: z.number().int().nullable().optional(),
});

export const carouselRetryAcceptedSchema = z.object({
  accepted: z.boolean(),
  retry_kind: z.string(),
  current_phase: z.string(),
  phase_status: z.string(),
  lock_version: z.number().int().nullable(),
  autopilot_run_id: z.string().nullable().optional(),
});

export type CarouselRetryCapability = z.infer<
  typeof carouselRetryCapabilitySchema
>;
export type CarouselRetryAccepted = z.infer<typeof carouselRetryAcceptedSchema>;
