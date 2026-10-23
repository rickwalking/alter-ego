import type { WorkflowColumnData } from "@/modules/editorial-operations/board/workflow/constants";
import type {
  KanbanCard as ApiKanbanCard,
  KanbanColumn as ApiKanbanColumn,
  WorkflowKanban,
} from "@/modules/editorial";
import type { KanbanColumn } from "@/schemas/neon-kanban";
import {
  ARCHIVE_REFUSAL,
  WORKFLOW_PHASE_STATUS,
  type ArchiveRefusal,
} from "@/constants/workflow";

const PUBLISHED_PHASE = "published";

function formatPhaseLabel(phase: string): string {
  return phase.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

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

/** Why the card cannot be archived, or `null` when it can. */
export function archiveRefusalOf(card: ApiKanbanCard): ArchiveRefusal | null {
  if (card.current_phase === PUBLISHED_PHASE) return ARCHIVE_REFUSAL.PUBLISHED;
  if (card.phase_status === WORKFLOW_PHASE_STATUS.IN_PROGRESS) {
    return ARCHIVE_REFUSAL.IN_PROGRESS;
  }
  return null;
}

export function mapApiKanbanColumn(column: ApiKanbanColumn): KanbanColumn {
  return {
    phase: column.phase,
    status: formatPhaseLabel(column.phase),
    count: column.cards.length,
    cards: column.cards.map((card: ApiKanbanCard) => ({
      id: card.id,
      title: card.title,
      description: card.topic,
      phase: card.current_phase,
      phaseStatus: card.workflow_status ?? card.phase_status,
      archiveRefusal: archiveRefusalOf(card),
    })),
  };
}

export function mapApiWorkflowKanbanToNeon(
  board: WorkflowKanban,
): KanbanColumn[] {
  return board.columns.map(mapApiKanbanColumn);
}
