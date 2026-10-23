"use client";

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { chatKeys } from "@/modules/conversation/queries";
import type { ChatStreamState } from "./types";

/** Re-read the history and the list (history on only): after a stop or a failure. */
export function useRefreshHistory(loadHistory: boolean): () => void {
  const queryClient = useQueryClient();
  return useCallback(() => {
    if (!loadHistory) return;
    void queryClient.invalidateQueries({ queryKey: chatKeys.allMessages() });
    void queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
  }, [loadHistory, queryClient]);
}

/**
 * Stop the reply in flight, keeping what already arrived on screen. The server
 * saves its reply for the turn; the history is re-read (and keeps polling
 * until that reply is saved) so it shows up.
 */
export function useStopStreaming(
  stream: ChatStreamState,
  loadHistory: boolean,
): () => void {
  const refreshHistory = useRefreshHistory(loadHistory);
  const { abortRef, setIsStreaming, resetStreamingRefs } = stream;
  return useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    resetStreamingRefs();
    refreshHistory();
  }, [abortRef, setIsStreaming, resetStreamingRefs, refreshHistory]);
}
