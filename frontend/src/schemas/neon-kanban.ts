import { z } from "zod";
import { neonBadgeVariantSchema } from "@/schemas/neon-badge";

export const kanbanCardSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  phase: z.string(),
  phaseStatus: z.string(),
  statusKey: z.string(),
  statusVariant: neonBadgeVariantSchema.optional(),
  statusPulse: z.boolean().optional(),
  updatedAt: z.string().nullable().optional(),
  assignee: z.string().optional(),
  archiveRefusal: z
    .enum(["published", "in_progress", "autopilot"])
    .nullable()
    .optional(),
  canArchive: z.boolean().optional(),
});

export const kanbanColumnSchema = z.object({
  phase: z.string(),
  status: z.string(),
  count: z.number().int().nonnegative().optional(),
  cards: z.array(kanbanCardSchema),
});

export type KanbanCard = z.infer<typeof kanbanCardSchema>;
export type KanbanColumn = z.infer<typeof kanbanColumnSchema>;
