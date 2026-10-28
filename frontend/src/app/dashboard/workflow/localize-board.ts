import type { KanbanCard, KanbanColumn } from "@/schemas/neon-kanban";
import type { NeonBadgeVariant } from "@/schemas/neon-badge";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
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
  /** Title of the Rejected column. */
  rejectedColumn: string;
  /** Title for a card whose title and topic are both empty. */
  untitled: string;
}

/** Board column the API fills with rejected projects. */
const BOARD_COLUMN_REJECTED = WORKFLOW_PHASE_STATUS.REJECTED;

function statusLabel(status: string, t: BoardTranslators): string {
  if (!KNOWN_WORKFLOW_STATUSES.includes(status)) {
    return titlecaseStatus(status);
  }
  const { labelKey } = resolveWorkflowStatusVisual(status);
  return labelKey ? t.status(labelKey) : titlecaseStatus(status);
}

interface BoardStatusVisual {
  variant?: NeonBadgeVariant;
  pulse?: boolean;
}

/**
 * The raw status drives the semantic badge treatment; an unrecognized status
 * keeps the neutral cyan instead of throwing on the board.
 */
function statusVisual(status: string): BoardStatusVisual {
  if (!KNOWN_WORKFLOW_STATUSES.includes(status)) {
    return {};
  }
  const { variant, pulse } = resolveWorkflowStatusVisual(status);
  return { variant, pulse };
}

function localizeCard(
  card: KanbanCard,
  t: BoardTranslators,
  labelFor: (card: KanbanCard) => string,
): KanbanCard {
  const { variant, pulse } = statusVisual(card.statusKey);
  return {
    ...card,
    title: card.title === "" ? t.untitled : card.title,
    phaseStatus: labelFor(card),
    statusVariant: variant,
    statusPulse: pulse,
  };
}

function phaseLabel(phase: string, t: BoardTranslators): string {
  return t.knownPhases.has(phase) ? t.phase(phase) : titlecaseStatus(phase);
}

/**
 * The workflow board shows phase names and status labels in
 * the dashboard language instead of raw snake_case ids
 * ("approved_for_publish" -> "Pronto para publicar"), and fills each card's
 * semantic badge variant from its raw workflow status.
 */
export function localizeBoardColumns(
  columns: readonly KanbanColumn[],
  t: BoardTranslators,
): KanbanColumn[] {
  return columns.map((column) =>
    column.phase === BOARD_COLUMN_REJECTED
      ? localizeRejectedColumn(column, t)
      : {
          ...column,
          status: phaseLabel(column.phase, t),
          cards: column.cards.map((card) =>
            localizeCard(card, t, (item) => statusLabel(item.statusKey, t)),
          ),
        },
  );
}

/**
 * Rejected projects have their own column, so each card's badge names
 * the phase it was rejected at instead of repeating "Rejected".
 */
function localizeRejectedColumn(
  column: KanbanColumn,
  t: BoardTranslators,
): KanbanColumn {
  return {
    ...column,
    status: t.rejectedColumn,
    cards: column.cards.map(
      (card): KanbanCard =>
        localizeCard(card, t, (item) => phaseLabel(item.phase, t)),
    ),
  };
}
