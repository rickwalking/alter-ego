"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";

import type { Message } from "@/schemas/chat";

import {
  appendStreamToken,
  beginStream,
  createOptimisticUserMessage,
  resetStreamRefs,
} from "./sse-chat-stream";

export interface ChatStream {
  optimisticMessages: Message[];
  setOptimisticMessages: Dispatch<SetStateAction<Message[]>>;
  isStreaming: boolean;
  setIsStreaming: Dispatch<SetStateAction<boolean>>;
  abortRef: MutableRefObject<AbortController | null>;
  /** Append the optimistic user message and begin a stream; returns its signal. */
  startUserTurn: (content: string) => AbortSignal;
  /** Fold a streamed token into the optimistic message list. */
  appendToken: (token: string) => void;
  /** Clear the per-stream accumulation refs (content + streaming message id). */
  resetStreamingRefs: () => void;
}

/**
 * Shared SSE chat streaming state (AE-0150). Owns the optimistic message list,
 * the streaming flag, the abort controller, and the per-stream accumulation
 * refs, and exposes the two operations both chat hooks perform identically:
 * starting a user turn and folding in streamed tokens. Hook-specific behavior
 * (history merge, finalize/invalidate, conversation creation, error handling)
 * stays in each consumer hook.
 */
export function useChatStream(
  userIdPrefix: string,
  streamIdPrefix: string,
): ChatStream {
  const [optimisticMessages, setOptimisticMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const contentRef = useRef("");
  const msgIdRef = useRef<string | null>(null);

  const startUserTurn = useCallback(
    (content: string): AbortSignal => {
      const userMsg = createOptimisticUserMessage(content, userIdPrefix);
      setOptimisticMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      abortRef.current = beginStream(
        { contentRef, msgIdRef },
        abortRef.current,
      );
      return abortRef.current.signal;
    },
    [userIdPrefix],
  );

  const appendToken = useCallback(
    (token: string): void => {
      contentRef.current += token;
      setOptimisticMessages((prev) => {
        const { messages, streamingMsgId } = appendStreamToken({
          messages: prev,
          token,
          accumulatedContent: contentRef.current,
          streamingMsgId: msgIdRef.current,
          newIdPrefix: streamIdPrefix,
        });
        msgIdRef.current = streamingMsgId;
        return messages;
      });
    },
    [streamIdPrefix],
  );

  const resetStreamingRefs = useCallback(() => {
    resetStreamRefs({ contentRef, msgIdRef });
  }, []);

  // Abort any in-flight stream when the consumer unmounts.
  useEffect(
    () => () => {
      abortRef.current?.abort();
    },
    [],
  );

  return {
    optimisticMessages,
    setOptimisticMessages,
    isStreaming,
    setIsStreaming,
    abortRef,
    startUserTurn,
    appendToken,
    resetStreamingRefs,
  };
}
