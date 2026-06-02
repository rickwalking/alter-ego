import { z } from "zod";

export const kanbanCardSchema = z.object({
  id: z.string(),
  title: z.string().min(1),
  description: z.string(),
  phase: z.string(),
  phaseStatus: z.string(),
  assignee: z.string().optional(),
});

export const kanbanColumnSchema = z.object({
  phase: z.string(),
  status: z.string(),
  count: z.number().int().nonnegative().optional(),
  cards: z.array(kanbanCardSchema),
});

export const neonKanbanPropsSchema = z.object({
  columns: z.array(kanbanColumnSchema).min(1),
});

export type KanbanCard = z.infer<typeof kanbanCardSchema>;
export type KanbanColumn = z.infer<typeof kanbanColumnSchema>;
