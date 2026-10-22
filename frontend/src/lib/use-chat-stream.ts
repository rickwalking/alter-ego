"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Dispatch, RefObject, SetStateAction } from "react";

import type { Message } from "@/schemas/chat";

import {
  appendStreamToken,
  beginStream,
  createOptimisticUserMessage,
  newStreamMessageId,
  resetStreamRefs,
} from "./sse-chat-stream";

export interface ChatStream {
  optimisticMessages: Message[];
  setOptimisticMessages: Dispatch<SetStateAction<Message[]>>;
  isStreaming: boolean;
  setIsStreaming: Dispatch<SetStateAction<boolean>>;
  abortRef: RefObject<AbortController | null>;
  /** Append the optimistic user message and begin a stream; returns its signal. */
  startUserTurn: (content: string) => AbortSignal;
  /** Fold a streamed token into the optimistic message list. */
  appendToken: (token: string) => void;
  /** Forget the streaming message id (the next token starts a new reply). */
  resetStreamingRefs: () => void;
}

/**
 * Shared SSE chat streaming state. Owns the optimistic message list,
 * the streaming flag, the abort controller, and the per-stream accumulation
 * refs, and exposes the two operations both chat hooks perform identically:
 * starting a user turn and folding in streamed tokens. Hook-specific behavior
 * (history merge, finalize/invalidate, conversation creation, error handling)
 * stays in each consumer hook.
 */
interface StreamTokens {
  msgIdRef: RefObject<string | null>;
  appendToken: (token: string) => void;
  resetStreamingRefs: () => void;
}

/**
 * The streaming message id and the token fold over it.
 *
 * The id is read when the token arrives, not inside the state updater, so
 * React batching (or a COMPLETE that resets the ref in the same batch) can
 * neither duplicate, drop nor split a reply.
 */
function useStreamTokens(
  streamIdPrefix: string,
  setOptimisticMessages: Dispatch<SetStateAction<Message[]>>,
): StreamTokens {
  const msgIdRef = useRef<string | null>(null);

  const appendToken = useCallback(
    (token: string): void => {
      msgIdRef.current ??= newStreamMessageId(streamIdPrefix);
      const streamingMsgId = msgIdRef.current;
      setOptimisticMessages((prev) =>
        appendStreamToken({ messages: prev, token, streamingMsgId }),
      );
    },
    [streamIdPrefix, setOptimisticMessages],
  );

  const resetStreamingRefs = useCallback(() => {
    resetStreamRefs({ msgIdRef });
  }, []);

  return { msgIdRef, appendToken, resetStreamingRefs };
}

/** Abort any in-flight stream when the consumer unmounts. */
function useAbortOnUnmount(abortRef: RefObject<AbortController | null>): void {
  useEffect(
    () => () => {
      abortRef.current?.abort();
    },
    [abortRef],
  );
}

interface UserTurnDeps {
  userIdPrefix: string;
  streamIdPrefix: string;
  tokens: StreamTokens;
  abortRef: RefObject<AbortController | null>;
}

/** Append the optimistic user message and begin a stream; returns its signal. */
function useStartUserTurn(
  { userIdPrefix, streamIdPrefix, tokens, abortRef }: UserTurnDeps,
  setOptimisticMessages: Dispatch<SetStateAction<Message[]>>,
  setIsStreaming: Dispatch<SetStateAction<boolean>>,
): (content: string) => AbortSignal {
  const { msgIdRef } = tokens;
  return useCallback(
    (content: string): AbortSignal => {
      const userMsg = createOptimisticUserMessage(content, userIdPrefix);
      setOptimisticMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      abortRef.current = beginStream(
        { msgIdRef },
        abortRef.current,
        streamIdPrefix,
      );
      return abortRef.current.signal;
    },
    [
      userIdPrefix,
      streamIdPrefix,
      msgIdRef,
      abortRef,
      setOptimisticMessages,
      setIsStreaming,
    ],
  );
}

export function useChatStream(
  userIdPrefix: string,
  streamIdPrefix: string,
): ChatStream {
  const [optimisticMessages, setOptimisticMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const tokens = useStreamTokens(streamIdPrefix, setOptimisticMessages);
  useAbortOnUnmount(abortRef);
  const startUserTurn = useStartUserTurn(
    { userIdPrefix, streamIdPrefix, tokens, abortRef },
    setOptimisticMessages,
    setIsStreaming,
  );

  return {
    optimisticMessages,
    setOptimisticMessages,
    isStreaming,
    setIsStreaming,
    abortRef,
    startUserTurn,
    appendToken: tokens.appendToken,
    resetStreamingRefs: tokens.resetStreamingRefs,
  };
}
