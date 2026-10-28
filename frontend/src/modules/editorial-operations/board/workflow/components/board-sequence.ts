"use client";

import { WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY } from "../constants";
import { safeStorageGet, safeStorageSet } from "./board-storage";

export interface BoardSequence {
  column: string;
  ids: string[];
}

/** Store the ordered cards from the column that owns the clicked card. */
export function saveBoardSequence(column: string, ids: string[]): void {
  const sequence: BoardSequence = { column, ids };
  safeStorageSet(
    window.sessionStorage,
    WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY,
    JSON.stringify(sequence),
  );
}

function parseSequence(raw: string | null): BoardSequence | null {
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

let cachedRaw: string | null = null;
let cachedSequence: BoardSequence | null = null;

/**
 * Referentially stable snapshot of the stored sequence for
 * `useSyncExternalStore`: the cached object only changes when the stored
 * string changes.
 */
export function boardSequenceSnapshot(): BoardSequence | null {
  const raw = safeStorageGet(
    window.sessionStorage,
    WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY,
  );
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cachedSequence = parseSequence(raw);
  }
  return cachedSequence;
}

/** Read a valid sequence, returning null for direct links or malformed state. */
export function loadBoardSequence(): BoardSequence | null {
  return parseSequence(
    safeStorageGet(window.sessionStorage, WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY),
  );
}
