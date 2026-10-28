"use client";

/**
 * Board scroll persistence across a card round trip. The board saves its
 * horizontal position and each column's vertical position right before a
 * card navigation and restores them once, after the first board load lands.
 */

import { WORKFLOW_BOARD_SCROLL_STORAGE_KEY } from "../constants";

export interface BoardScrollPosition {
  left: number;
  tops: Record<string, number>;
}

export function saveBoardScroll(
  board: HTMLElement,
  columnTops: Record<string, number>,
): void {
  const position: BoardScrollPosition = {
    left: board.scrollLeft,
    tops: columnTops,
  };
  window.sessionStorage.setItem(
    WORKFLOW_BOARD_SCROLL_STORAGE_KEY,
    JSON.stringify(position),
  );
}

export function loadSavedBoardScroll(): BoardScrollPosition | null {
  const raw = window.sessionStorage.getItem(WORKFLOW_BOARD_SCROLL_STORAGE_KEY);
  if (raw === null) return null;
  try {
    const parsed = JSON.parse(raw) as BoardScrollPosition;
    if (typeof parsed.left !== "number" || typeof parsed.tops !== "object") {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function applyBoardScroll(
  board: HTMLElement,
  columns: Record<string, HTMLElement>,
  position: BoardScrollPosition,
): void {
  board.scrollLeft = position.left;
  for (const [key, element] of Object.entries(columns)) {
    const top = position.tops[key];
    if (typeof top === "number") element.scrollTop = top;
  }
  window.sessionStorage.removeItem(WORKFLOW_BOARD_SCROLL_STORAGE_KEY);
}
