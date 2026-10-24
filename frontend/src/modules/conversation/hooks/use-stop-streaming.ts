"use client";

import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { chatKeys } from "@/modules/conversation/queries";
import type { ChatStreamState, NewChatDeps, StopControl } from "./types";

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
 * The Stop control. Stop is offered once the answer stream has opened (before
 * that a stop would lose the message), and stopping keeps what arrived on
 * screen. The server saves its reply for the turn; the history is re-read (and
 * keeps polling until that reply is saved) so it shows up, and until then the
 * turn counts as still being answered.
 */
export function useStopControl(
  stream: ChatStreamState,
  loadHistory: boolean,
): StopControl {
  const refreshHistory = useRefreshHistory(loadHistory);
  const { abortRef, setIsStreaming, resetStreamingRefs } = stream;
  const [streamOpen, setStreamOpen] = useState(false);
  const [stopped, setStopped] = useState(false);
  const stoppedRef = useRef(false);
  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    resetStreamingRefs();
    stoppedRef.current = true;
    setStopped(true);
    refreshHistory();
  }, [abortRef, setIsStreaming, resetStreamingRefs, refreshHistory]);
  const markOpen = useCallback(() => {
    setStreamOpen(true);
  }, []);
  const beginTurn = useCallback((): boolean => {
    const wasStopped = stoppedRef.current;
    stoppedRef.current = false;
    setStopped(false);
    setStreamOpen(false);
    return wasStopped;
  }, []);
  return { stopStreaming, streamOpen, stopped, markOpen, beginTurn };
}

/** Abort the turn in flight and clear the chat (stale refetches see a new turn). */
export function useStartNewChat({
  stream,
  turnRef,
  setError,
  beginTurn,
}: NewChatDeps): () => void {
  const { abortRef, setOptimisticMessages, setIsStreaming } = stream;
  const { resetStreamingRefs } = stream;
  return useCallback(() => {
    beginTurn();
    turnRef.current += 1;
    abortRef.current?.abort();
    setOptimisticMessages([]);
    setIsStreaming(false);
    setError(null);
    resetStreamingRefs();
  }, [
    turnRef,
    abortRef,
    setOptimisticMessages,
    setIsStreaming,
    setError,
    resetStreamingRefs,
    beginTurn,
  ]);
}
