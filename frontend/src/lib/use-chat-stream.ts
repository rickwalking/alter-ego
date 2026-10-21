"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Dispatch, RefObject, SetStateAction } from "react";

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
  abortRef: RefObject<AbortController | null>;
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
interface StreamTokens {
  contentRef: MutableRefObject<string>;
  msgIdRef: MutableRefObject<string | null>;
  appendToken: (token: string) => void;
  resetStreamingRefs: () => void;
}

interface TokenFoldRefs {
  contentRef: MutableRefObject<string>;
  msgIdRef: MutableRefObject<string | null>;
  streamIdPrefix: string;
}

/** Fold one token into the message list, remembering the streaming id. */
function foldToken(
  prev: Message[],
  token: string,
  { contentRef, msgIdRef, streamIdPrefix }: TokenFoldRefs,
): Message[] {
  const { messages, streamingMsgId } = appendStreamToken({
    messages: prev,
    token,
    accumulatedContent: contentRef.current,
    streamingMsgId: msgIdRef.current,
    newIdPrefix: streamIdPrefix,
  });
  msgIdRef.current = streamingMsgId;
  return messages;
}

/** The per-stream accumulation refs and the token fold over them. */
function useStreamTokens(
  streamIdPrefix: string,
  setOptimisticMessages: Dispatch<SetStateAction<Message[]>>,
): StreamTokens {
  const contentRef = useRef("");
  const msgIdRef = useRef<string | null>(null);

  const appendToken = useCallback(
    (token: string): void => {
      contentRef.current += token;
      setOptimisticMessages((prev) =>
        foldToken(prev, token, { contentRef, msgIdRef, streamIdPrefix }),
      );
    },
    [streamIdPrefix, setOptimisticMessages],
  );

  const resetStreamingRefs = useCallback(() => {
    resetStreamRefs({ contentRef, msgIdRef });
  }, []);

  return { contentRef, msgIdRef, appendToken, resetStreamingRefs };
}

/** Abort any in-flight stream when the consumer unmounts. */
function useAbortOnUnmount(
  abortRef: MutableRefObject<AbortController | null>,
): void {
  useEffect(
    () => () => {
      abortRef.current?.abort();
    },
    [abortRef],
  );
}

interface UserTurnDeps {
  userIdPrefix: string;
  tokens: StreamTokens;
  abortRef: MutableRefObject<AbortController | null>;
}

/** Append the optimistic user message and begin a stream; returns its signal. */
function useStartUserTurn(
  { userIdPrefix, tokens, abortRef }: UserTurnDeps,
  setOptimisticMessages: Dispatch<SetStateAction<Message[]>>,
  setIsStreaming: Dispatch<SetStateAction<boolean>>,
): (content: string) => AbortSignal {
  const { contentRef, msgIdRef } = tokens;
  return useCallback(
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
    [
      userIdPrefix,
      contentRef,
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
    { userIdPrefix, tokens, abortRef },
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
