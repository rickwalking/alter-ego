import type { WorkflowColumnData } from "@/features/dashboard/workflow/constants";
import type { KanbanColumn } from "@/schemas/neon-kanban";

export interface WorkflowCardSource {
  id: string;
  title: string;
  description: string;
  phase: string;
  phaseStatus: string;
  assignee?: string;
}

export interface WorkflowColumnSource {
  phase: string;
  status: string;
  cards: WorkflowCardSource[];
}

export function mapWorkflowColumnDataToKanban(
  columns: WorkflowColumnData[],
): KanbanColumn[] {
  return columns.map((column) => ({
    phase: column.id,
    status: column.label,
    count: column.cards.length,
    cards: column.cards.map((card, index) => ({
      id: `${column.id}-${index}`,
      title: card.title,
      description: card.description,
      phase: card.phase,
      phaseStatus: card.approvalStatus,
      assignee: card.assignee,
    })),
  }));
}

export function mapWorkflowToKanbanColumns(
  columns: WorkflowColumnSource[],
): KanbanColumn[] {
  return columns.map((column) => ({
    phase: column.phase,
    status: column.status,
    count: column.cards.length,
    cards: column.cards.map((card) => ({
      id: card.id,
      title: card.title,
      description: card.description,
      phase: card.phase,
      phaseStatus: card.phaseStatus,
      assignee: card.assignee,
    })),
  }));
}
