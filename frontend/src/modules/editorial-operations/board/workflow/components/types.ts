/**
 * Component prop types for the workflow board (colocated `types.ts`).
 */

import type { KeyboardEvent, ReactNode } from "react";
import type { KanbanCard, KanbanColumn } from "@/schemas/neon-kanban";

export interface NeonKanbanBoardProps {
  columns: KanbanColumn[];
  /** Controls shown under a card, outside its link (e.g. archive). */
  renderCardActions?: (card: KanbanCard) => ReactNode;
  /** Localized strings the board itself renders (rails, empty columns). */
  labels: BoardColumnLabels;
  /**
   * Board view identity for the saved scroll position (active vs archived),
   * so Back never applies the archived scroll to the active board.
   */
  viewKey?: string;
}

export interface BoardColumnLabels {
  /** Text shown inside an expanded empty column. */
  emptyColumn: string;
  /** Accessible rail label naming the column and its card count. */
  expandColumn: (name: string, count: number) => string;
  /** Accessible label of the collapse control on an expanded column. */
  collapseColumn: (name: string) => string;
  /** Localized "N need you" for column headers with awaiting-human cards. */
  needYou?: (count: number) => string;
  /** Localized item count announced on the column card list. */
  columnCount: (count: number) => string;
}

export interface WorkflowBoardColumnProps {
  column: KanbanColumn;
  collapsed: boolean;
  labels: BoardColumnLabels;
  onToggle: (key: string) => void;
  onCardClick: (column: KanbanColumn) => void;
  setColumnRef: (key: string, element: HTMLDivElement | null) => void;
  renderCardActions?: (card: KanbanCard) => ReactNode;
  /** The only card link kept in the tab order (roving keyboard focus). */
  tabbableCardId: string | null;
  /** Registers a card link element for arrow-key focus moves. */
  registerCard: (id: string, element: HTMLElement | null) => void;
}

/** Keyboard navigation state and callbacks for the board card grid. */
export interface BoardRovingFocus {
  tabbableCardId: string | null;
  registerCard: (id: string, element: HTMLElement | null) => void;
  onBoardKeyDown: (event: KeyboardEvent<HTMLElement>) => void;
}

/** A card's coordinates in the non-empty-column grid. */
export interface BoardCardPosition {
  readonly column: number;
  readonly row: number;
}

/** The outcome of resolving a key press on a board card. */
export interface BoardKeyResult {
  readonly click: boolean;
  readonly focusId: string | null;
}

/** The card link element a keyboard event bubbled from. */
export interface BoardCardLinkTarget {
  readonly link: Element;
  readonly cardId: string;
}
