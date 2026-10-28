"use client";

import { useCallback, useLayoutEffect, useRef, useState } from "react";
import {
  WORKFLOW_BOARD_DONE_PHASES,
  WORKFLOW_BOARD_EXPANDED_STORAGE_KEY,
} from "../constants";
import {
  applyBoardScroll,
  loadSavedBoardScroll,
  saveBoardScroll,
} from "./board-scroll";
import { saveBoardSequence } from "./board-sequence";
import { safeStorageGet, safeStorageSet } from "./board-storage";
import { WorkflowBoardColumn } from "./workflow-board-column";
import type { KanbanColumn } from "@/schemas/neon-kanban";
import type { NeonKanbanBoardProps } from "./types";

export type { NeonKanbanBoardProps } from "./types";

const BOARD_SCROLL_TEST_ID = "workflow-board-scroll";
const DEFAULT_BOARD_VIEW_KEY = "active";

function isRailColumn(
  column: KanbanColumn,
  expanded: ReadonlySet<string>,
): boolean {
  if (expanded.has(column.phase)) return false;
  return (
    column.cards.length === 0 || WORKFLOW_BOARD_DONE_PHASES.has(column.phase)
  );
}

function readExpandedColumns(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = safeStorageGet(
      window.localStorage,
      WORKFLOW_BOARD_EXPANDED_STORAGE_KEY,
    );
    const parsed = raw === null ? [] : (JSON.parse(raw) as unknown);
    return Array.isArray(parsed)
      ? parsed.filter((key): key is string => typeof key === "string")
      : [];
  } catch {
    return [];
  }
}

/** A viewport-bound board with independent columns and persistent navigation. */
export function NeonKanbanBoard({
  columns,
  renderCardActions,
  labels,
  viewKey = DEFAULT_BOARD_VIEW_KEY,
}: Readonly<NeonKanbanBoardProps>): React.ReactElement {
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(
    () => new Set(readExpandedColumns()),
  );
  const boardScrollRef = useRef<HTMLDivElement | null>(null);
  const columnRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const restoredRef = useRef(false);
  const setColumnRef = useCallback(
    (key: string, element: HTMLDivElement | null): void => {
      columnRefs.current[key] = element;
    },
    [],
  );

  useLayoutEffect(() => {
    if (restoredRef.current) return;
    if (!columns.some((column) => column.cards.length > 0)) return;
    restoredRef.current = true;
    const board = boardScrollRef.current;
    const saved = board === null ? null : loadSavedBoardScroll(viewKey);
    if (board === null || saved === null) return;
    const liveColumns: Record<string, HTMLElement> = {};
    for (const [key, element] of Object.entries(columnRefs.current)) {
      if (element !== null) liveColumns[key] = element;
    }
    applyBoardScroll({
      board,
      columns: liveColumns,
      position: saved,
      view: viewKey,
    });
  }, [columns, viewKey]);

  const toggleColumn = useCallback((key: string): void => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      safeStorageSet(
        window.localStorage,
        WORKFLOW_BOARD_EXPANDED_STORAGE_KEY,
        JSON.stringify([...next]),
      );
      return next;
    });
  }, []);

  const rememberScroll = useCallback((): void => {
    const board = boardScrollRef.current;
    if (board === null) return;
    const tops: Record<string, number> = {};
    for (const [key, element] of Object.entries(columnRefs.current)) {
      if (element !== null) tops[key] = element.scrollTop;
    }
    saveBoardScroll(board, tops, viewKey);
  }, [viewKey]);

  const rememberColumn = useCallback(
    (column: KanbanColumn): void => {
      rememberScroll();
      saveBoardSequence(
        column.status,
        column.cards.map((card) => card.id),
      );
    },
    [rememberScroll],
  );

  return (
    <div
      ref={boardScrollRef}
      data-testid={BOARD_SCROLL_TEST_ID}
      className="flex h-full min-h-0 gap-4 overflow-x-auto overflow-y-hidden pb-2"
    >
      {columns.map((column) => (
        <WorkflowBoardColumn
          key={column.phase}
          column={column}
          collapsed={isRailColumn(column, expanded)}
          labels={labels}
          onToggle={toggleColumn}
          onCardClick={rememberColumn}
          setColumnRef={setColumnRef}
          renderCardActions={renderCardActions}
        />
      ))}
    </div>
  );
}
