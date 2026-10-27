import { z } from "zod";

const generationEventDetailSchema = z.union([
  z.string(),
  z.number(),
  z.boolean(),
]);

const generationEventSchema = z.object({
  id: z.string(),
  generation_run_id: z.string(),
  event_type: z.string(),
  phase: z.string().nullable(),
  outcome: z.string(),
  occurred_at: z.string(),
  duration_ms: z.number().nullable(),
  attempt: z.number().nullable(),
  error_code: z.string().nullable(),
  message_code: z.string().nullable(),
  details: z.record(z.string(), generationEventDetailSchema),
  langfuse_trace_id: z.string().nullable(),
  langfuse_trace_url: z.string().nullable(),
});

const generationRunSchema = z.object({
  id: z.string(),
  kind: z.string(),
  status: z.string(),
  queued_at: z.string(),
  started_at: z.string().nullable(),
  finished_at: z.string().nullable(),
  duration_ms: z.number().nullable(),
  attempts: z.number(),
  error_code: z.string().nullable(),
});

export const carouselGenerationLogResponseSchema = z.object({
  project_id: z.string(),
  events: z.array(generationEventSchema),
  runs: z.array(generationRunSchema),
  next_cursor: z.string().nullable(),
});

export type GenerationLogEvent = z.infer<typeof generationEventSchema>;
export type GenerationLogRun = z.infer<typeof generationRunSchema>;
export type GenerationLogPage = z.infer<
  typeof carouselGenerationLogResponseSchema
>;
