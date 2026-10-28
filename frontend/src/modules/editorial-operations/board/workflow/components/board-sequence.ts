"use client";

import { WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY } from "../constants";

export interface BoardSequence {
  column: string;
  ids: string[];
}

/** Store the ordered cards from the column that owns the clicked card. */
export function saveBoardSequence(column: string, ids: string[]): void {
  const sequence: BoardSequence = { column, ids };
  window.sessionStorage.setItem(
    WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY,
    JSON.stringify(sequence),
  );
}

/** Read a valid sequence, returning null for direct links or malformed state. */
export function loadBoardSequence(): BoardSequence | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(
    WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY,
  );
  if (raw === null) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (typeof parsed !== "object" || parsed === null) return null;
    const candidate = parsed as Partial<BoardSequence>;
    if (typeof candidate.column !== "string") return null;
    if (
      !Array.isArray(candidate.ids) ||
      !candidate.ids.every((id) => typeof id === "string")
    ) {
      return null;
    }
    return { column: candidate.column, ids: candidate.ids };
  } catch {
    return null;
  }
}
