import type { FocusEvent, KeyboardEvent, RefObject } from "react";
import type { WorkflowPostActionResult } from "@/modules/editorial";
import type { KanbanCard } from "@/schemas/neon-kanban";

/** The archive control under one workflow board card. */
export interface CardArchiveActionProps {
  card: KanbanCard;
  /** The board lists archived carousels (restore) instead of active ones. */
  archived: boolean;
  /** Called once the archive or restore went through. */
  onChanged: () => void;
  /**
   * Whether the trigger holds the board's single roving-control tab stop;
   * standalone usage leaves it tabbable.
   */
  tabbable?: boolean;
}

/** The board of the workflow page, active or archived. */
export interface WorkflowBoardViewProps {
  archived: boolean;
}

/** The board's first-load and failure feedback. */
export interface BoardFeedbackProps {
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

/** The Ativos | Arquivados segmented control in the board top bar. */
export interface WorkflowViewSwitchProps {
  /** Whether the archived board view is active. */
  archived: boolean;
}

/** The menu items rendered inside a card's overflow menu. */
export interface CardArchiveMenuItemsProps {
  card: KanbanCard;
  /** The board lists archived carousels (restore) instead of active ones. */
  archived: boolean;
  /** Whether the archive confirmation step is showing. */
  confirming: boolean;
  onConfirmingChange: (confirming: boolean) => void;
  archive: WorkflowPostActionResult;
  restore: WorkflowPostActionResult;
}

/** State and callbacks of a card's overflow menu shell. */
export interface CardOverflowMenu {
  open: boolean;
  confirming: boolean;
  onConfirmingChange: (confirming: boolean) => void;
  triggerRef: RefObject<HTMLButtonElement | null>;
  menuRef: RefObject<HTMLDivElement | null>;
  position: MenuPosition;
  openMenu: () => void;
  closeMenu: (returnFocus: boolean) => void;
  onMenuKeyDown: (event: KeyboardEvent<HTMLDivElement>) => void;
  onMenuBlur: (event: FocusEvent<HTMLDivElement>) => void;
}

/** Fixed viewport position of the open overflow menu. */
export interface MenuPosition {
  readonly top: number;
  readonly left: number;
}

/** Refs the menu dismissal effect needs while the menu is open. */
export interface MenuDismissalRefs {
  readonly menuRef: RefObject<HTMLDivElement | null>;
  readonly triggerRef: RefObject<HTMLButtonElement | null>;
}
