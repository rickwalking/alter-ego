"use client";

/**
 * Hook for workflow Kanban board (UI-018).
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  WORKFLOW_API,
  WORKFLOW_BOARD_POLL_INTERVAL_MS,
} from "@/constants/workflow";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

export type KanbanCard = {
  id: string;
  title: string;
  topic: string;
  current_phase: string;
  phase_status: string;
  workflow_status?: string | null;
  updated_at: string | null;
};

export type KanbanColumn = {
  phase: string;
  cards: KanbanCard[];
};

export type WorkflowKanban = {
  columns: KanbanColumn[];
};

export function useWorkflowKanban() {
  const t = useTranslations("workflow.errors");
  const [board, setBoard] = useState<WorkflowKanban | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBoard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(WORKFLOW_API.WORKFLOW_BOARD);
      if (!response.ok) {
        throw new Error(t("loadBoardFailed"));
      }
      const data = (await response.json()) as WorkflowKanban;
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
