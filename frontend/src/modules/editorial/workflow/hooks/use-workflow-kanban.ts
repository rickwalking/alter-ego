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

/**
 * Loads the board and refreshes it on a poll and on window focus. Only the
 * first load reports `loading`; refetches swap the data in place so the
 * mounted board (and the page scroll) survives every poll.
 */
export function useWorkflowKanban() {
  const t = useTranslations("workflow.errors");
  const [board, setBoard] = useState<WorkflowKanban | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasBoardRef = useRef(false);

  const fetchBoard = useCallback(async () => {
    if (!hasBoardRef.current) {
      setLoading(true);
    }
    setError(null);
    try {
      const response = await authenticatedFetch(WORKFLOW_API.WORKFLOW_BOARD);
      if (!response.ok) {
        throw new Error(t("loadBoardFailed"));
      }
      const data = (await response.json()) as WorkflowKanban;
      hasBoardRef.current = true;
      setBoard(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("unknown"));
    } finally {
      setLoading(false);
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
