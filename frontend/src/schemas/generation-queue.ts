import { z } from "zod";

const timestamp = z.iso.datetime({ offset: true, local: true });

/** One generation run on the dashboard's queue panel, with its buttons. */
export const queueItemSchema = z.object({
  id: z.string(),
  kind: z.string(),
  status: z.string(),
  title: z.string(),
  project_id: z.string().nullable(),
  phase: z.string().nullable(),
  position: z.number().int().nullable(),
  eta: timestamp.nullable(),
  started_at: timestamp.nullable(),
  next_attempt_at: timestamp.nullable(),
  run_heartbeat_at: timestamp.nullable(),
  lock_version: z.number().int().nullable(),
  error_code: z.string().nullable(),
  staged: z.boolean(),
  autopilot_run_id: z.string().nullable(),
  priority: z.number().int(),
  can_reprocess: z.boolean(),
  refusal_code: z.string().nullable(),
  stuck_kind: z.string().nullable(),
  can_retry: z.boolean(),
  can_discard: z.boolean(),
  can_cancel: z.boolean(),
});

/** A theme waiting in the backlog for the next free slot. */
export const backlogItemSchema = z.object({
  candidate_id: z.string(),
  title: z.string(),
  created_at: timestamp,
  expires_at: timestamp,
});

/** The whole queue panel. */
export const queueBoardResponseSchema = z.object({
  active: z.array(queueItemSchema),
  dead: z.array(queueItemSchema),
  backlog: z.array(backlogItemSchema),
  average_drive_minutes: z.number(),
});

/** What a panel button did. */
export const queueActionResponseSchema = z.object({
  outcome: z.string(),
});

export const queueMaintenanceResponseSchema = z.object({
  outcome: z.enum(["queued", "existing"]),
  job_id: z.number().int(),
});

export type QueueItem = z.infer<typeof queueItemSchema>;
export type BacklogItem = z.infer<typeof backlogItemSchema>;
export type QueueBoard = z.infer<typeof queueBoardResponseSchema>;
