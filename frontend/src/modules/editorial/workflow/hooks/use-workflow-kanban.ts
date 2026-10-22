"use client";

/**
 * Hook for workflow Kanban board (UI-018).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import {
  WORKFLOW_API,
  WORKFLOW_BOARD_POLL_INTERVAL_MS,
} from "@/constants/workflow";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type { WorkflowKanban } from "./types";

async function requestBoard(failedText: string): Promise<WorkflowKanban> {
  const response = await authenticatedFetch(WORKFLOW_API.WORKFLOW_BOARD);
  if (!response.ok) {
    throw new Error(failedText);
  }
  return (await response.json()) as WorkflowKanban;
}

/**
 * Loads the board and refreshes it on a poll and on window focus. Only the
 * first load reports `loading`; refetches swap the data in place so the
 * mounted board (and the page scroll) survives every poll. An error stays
 * until a refresh succeeds (no flicker between failed polls), and only the
 * newest request may update the board, so a late older answer is dropped.
 */
export function useWorkflowKanban() {
  const t = useTranslations("workflow.errors");
  const [board, setBoard] = useState<WorkflowKanban | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasBoardRef = useRef(false);
  const latestRequestRef = useRef(0);

  const fetchBoard = useCallback(async () => {
    const requestId = latestRequestRef.current + 1;
    latestRequestRef.current = requestId;
    if (!hasBoardRef.current) {
      setLoading(true);
    }
    try {
      const data = await requestBoard(t("loadBoardFailed"));
      if (requestId !== latestRequestRef.current) return;
      hasBoardRef.current = true;
      setBoard(data);
      setError(null);
    } catch (err) {
      if (requestId !== latestRequestRef.current) return;
      setError(err instanceof Error ? err.message : t("unknown"));
    } finally {
      if (requestId === latestRequestRef.current) setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void fetchBoard();
    const intervalId = window.setInterval(() => {
      void fetchBoard();
    }, WORKFLOW_BOARD_POLL_INTERVAL_MS);
    const handleFocus = (): void => {
      void fetchBoard();
    };
    window.addEventListener("focus", handleFocus);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", handleFocus);
    };
  }, [fetchBoard]);

  return { board, loading, error, refetch: fetchBoard };
}
