import type { WorkflowColumnData } from "@/modules/editorial-operations/board/workflow/constants";
import type {
  KanbanCard as ApiKanbanCard,
  KanbanColumn as ApiKanbanColumn,
  WorkflowKanban,
} from "@/modules/editorial";
import type { KanbanColumn } from "@/schemas/neon-kanban";
import { ARCHIVE_REFUSAL, type ArchiveRefusal } from "@/constants/workflow";

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

const ARCHIVE_REFUSALS: readonly string[] = Object.values(ARCHIVE_REFUSAL);

/** The board API's archive refusal for the card, or `null` when it can be archived. */
export function archiveRefusalOf(card: ApiKanbanCard): ArchiveRefusal | null {
  const refusal = card.archive_refusal ?? null;
  if (refusal === null || !ARCHIVE_REFUSALS.includes(refusal)) return null;
  return refusal as ArchiveRefusal;
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
      canArchive: card.can_archive ?? false,
    })),
  };
}

export function mapApiWorkflowKanbanToNeon(
  board: WorkflowKanban,
): KanbanColumn[] {
  return board.columns.map(mapApiKanbanColumn);
}
