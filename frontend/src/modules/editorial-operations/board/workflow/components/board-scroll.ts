"use client";

/**
 * Board scroll persistence across a card round trip, keyed by board view
 * (active or archived) so returning to the active board never applies the
 * archived view's scroll. The board saves its horizontal position and each
 * column's vertical position right before a card navigation and restores them
 * once, after the first board load lands. A disabled or full storage, or a
 * corrupt payload, is ignored instead of breaking the board.
 */

import { WORKFLOW_BOARD_SCROLL_STORAGE_PREFIX } from "../constants";
import {
  safeStorageGet,
  safeStorageRemove,
  safeStorageSet,
} from "./board-storage";

export interface BoardScrollPosition {
  left: number;
  tops: Record<string, number>;
}

export function boardScrollStorageKey(view: string): string {
  return `${WORKFLOW_BOARD_SCROLL_STORAGE_PREFIX}:${view}`;
}

export function saveBoardScroll(
  board: HTMLElement,
  columnTops: Record<string, number>,
  view: string,
): void {
  const position: BoardScrollPosition = {
    left: board.scrollLeft,
    tops: columnTops,
  };
  safeStorageSet(
    window.sessionStorage,
    boardScrollStorageKey(view),
    JSON.stringify(position),
  );
}

/** A stored position, or null when nothing valid is stored for the view. */
export function loadSavedBoardScroll(view: string): BoardScrollPosition | null {
  const raw = safeStorageGet(
    window.sessionStorage,
    boardScrollStorageKey(view),
  );
  if (raw === null) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (typeof parsed !== "object" || parsed === null) return null;
    const candidate = parsed as { left?: unknown; tops?: unknown };
    if (typeof candidate.left !== "number") return null;
    if (typeof candidate.tops !== "object" || candidate.tops === null) {
      return null;
    }
    const tops: Record<string, number> = {};
    for (const [key, value] of Object.entries(
      candidate.tops as Record<string, unknown>,
    )) {
      if (typeof value !== "number") continue;
      tops[key] = value;
    }
    return { left: candidate.left, tops };
  } catch {
    return null;
  }
}

export interface ApplyBoardScrollInput {
  board: HTMLElement;
  columns: Record<string, HTMLElement>;
  position: BoardScrollPosition;
  view: string;
}

export function applyBoardScroll({
  board,
  columns,
  position,
  view,
}: Readonly<ApplyBoardScrollInput>): void {
  board.scrollLeft = position.left;
  for (const [key, element] of Object.entries(columns)) {
    const top = position.tops[key];
    if (typeof top === "number") element.scrollTop = top;
  }
  safeStorageRemove(window.sessionStorage, boardScrollStorageKey(view));
}
