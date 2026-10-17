import type { KanbanColumn } from "@/schemas/neon-kanban";
import {
  KNOWN_WORKFLOW_STATUSES,
  resolveWorkflowStatusVisual,
  titlecaseStatus,
} from "@/app/dashboard/create/workspace/workflow-status";

type Translate = (key: string) => string;

export interface BoardTranslators {
  /** `create.phases` — phase id -> name. */
  phase: Translate;
  /** `create.status` — status label key -> label. */
  status: Translate;
  /** Phase ids with a `create.phases` entry. */
  knownPhases: ReadonlySet<string>;
}

function statusLabel(status: string, t: BoardTranslators): string {
  if (!KNOWN_WORKFLOW_STATUSES.includes(status)) {
    return titlecaseStatus(status);
  }
  const { labelKey } = resolveWorkflowStatusVisual(status);
  return labelKey ? t.status(labelKey) : titlecaseStatus(status);
}

function phaseLabel(phase: string, t: BoardTranslators): string {
  return t.knownPhases.has(phase) ? t.phase(phase) : titlecaseStatus(phase);
}

/**
 * AE-0415 (B24): the workflow board shows phase names and status labels in
 * the dashboard language instead of raw snake_case ids
 * ("approved_for_publish" -> "Pronto para publicar").
 */
export function localizeBoardColumns(
  columns: readonly KanbanColumn[],
  t: BoardTranslators,
): KanbanColumn[] {
  return columns.map((column) => ({
    ...column,
    status: phaseLabel(column.phase, t),
    cards: column.cards.map((card) => ({
      ...card,
      phaseStatus: statusLabel(card.phaseStatus, t),
    })),
  }));
}
