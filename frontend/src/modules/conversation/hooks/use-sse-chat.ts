"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useConversationMessages } from "@/modules/conversation/hooks/use-chat";
import { chatKeys } from "@/modules/conversation/queries";
import { streamSseEvents, SSE_EVENT_TYPE } from "@/lib/sse-client";
import { useChatStream } from "@/lib/use-chat-stream";
import {
  dispatchSseEvent,
  sseContentText,
  type SseEventData,
  type SseEventHandlers,
} from "@/lib/sse-event-data";
import { API_ENDPOINTS } from "@/constants/api";
import type { Message } from "@/schemas/chat";
import type {
  ChatStreamState,
  ChatTurnCallbacks,
  SendChatDeps,
  UseSseChatOptions,
  UseSseChatReturn,
} from "./types";

const SSE_CHAT_USER_ID_PREFIX = "user-";
const STREAM_MESSAGE_ID_PREFIX = "stream-";

export type { UseSseChatOptions, UseSseChatReturn } from "./types";

function mergeMessages(
  historyMessages: Message[],
  optimisticMessages: Message[],
): Message[] {
  if (optimisticMessages.length === 0) {
    return historyMessages;
  }

  const seen = new Set(
    historyMessages.map((message) => `${message.role}:${message.content}`),
  );
  const uniqueOptimistic = optimisticMessages.filter(
    (message) => !seen.has(`${message.role}:${message.content}`),
  );

  return [...historyMessages, ...uniqueOptimistic];
}

/** Attach the streamed sources to the trailing assistant message. */
function withAssistantSources(
  prev: Message[],
  sources: Message["sources"],
): Message[] {
  const last = prev[prev.length - 1];
  if (last?.role !== "assistant") {
    return prev;
  }
  return [...prev.slice(0, -1), { ...last, sources: sources ?? [] }];
}

/** Backend sends sources in data.content (e.g. {"type":"sources","content":[]}). */
function streamedSources(data: SseEventData): Message["sources"] {
  return data.sources ?? data.content;
}

/** The persisted history when enabled (an empty list otherwise). */
function useHistory(
  loadHistory: boolean,
  conversationId: string | null,
): Message[] {
  const { data: fetchedHistory = [] } = useConversationMessages(
    loadHistory ? conversationId : null,
  );
  return useMemo(
    () => (loadHistory ? fetchedHistory : []),
    [loadHistory, fetchedHistory],
  );
}

/**
 * End a stream once (COMPLETE and the reader's onComplete both fire); with
 * history on, refetch it and then drop the optimistic copies.
 */
function useFinalizeStream(
  stream: ChatStreamState,
  loadHistory: boolean,
): {
  finalizedRef: RefObject<boolean>;
  finalizeStream: (convId: string) => void;
} {
  const queryClient = useQueryClient();
  const finalizedRef = useRef(false);
  const { setIsStreaming, resetStreamingRefs, setOptimisticMessages } = stream;
  const finalizeStream = useCallback(
    (convId: string) => {
      if (finalizedRef.current) {
        return;
      }
      finalizedRef.current = true;
      setIsStreaming(false);
      resetStreamingRefs();
      if (!loadHistory) {
        return;
      }
      void queryClient
        .invalidateQueries({ queryKey: chatKeys.messages(convId) })
        .then(() => {
          setOptimisticMessages([]);
        });
    },
    [
      loadHistory,
      queryClient,
      setIsStreaming,
      resetStreamingRefs,
      setOptimisticMessages,
    ],
  );
  return { finalizedRef, finalizeStream };
}

/** The SSE handlers for one chat turn of conversation ``convId``. */
function chatTurnHandlers(
  turn: ChatTurnCallbacks,
  convId: string,
): SseEventHandlers {
  return {
    [SSE_EVENT_TYPE.TOKEN]: (data) =>
      turn.appendToken(sseContentText(data, "")),
    [SSE_EVENT_TYPE.SOURCES]: (data) =>
      turn.setOptimisticMessages((prev) =>
        withAssistantSources(prev, streamedSources(data)),
      ),
    [SSE_EVENT_TYPE.COMPLETE]: () => turn.finalizeStream(convId),
    [SSE_EVENT_TYPE.ERROR]: (data) =>
      failStream(turn, sseContentText(data, "Unknown error")),
  };
}

/** Show the error and end the stream. */
function failStream(turn: ChatTurnCallbacks, message: string): void {
  turn.setError(message);
  turn.setIsStreaming(false);
  turn.resetStreamingRefs();
}

/** Stream one user turn into the conversation, folding each SSE event in. */
function useSendChatMessage({
  stream,
  conversationId,
  isStreaming,
  setError,
  finalizedRef,
  finalizeStream,
}: SendChatDeps): UseSseChatReturn["sendMessage"] {
  const { startUserTurn, appendToken, setOptimisticMessages } = stream;
  const { setIsStreaming, resetStreamingRefs } = stream;
  return useCallback(
    async (content: string, overrideConversationId?: string) => {
      const convId = overrideConversationId ?? conversationId;
      if (!content.trim() || isStreaming || !convId) return;
      finalizedRef.current = false;
      setError(null);
      const turn: ChatTurnCallbacks = {
        appendToken,
        setOptimisticMessages,
        setIsStreaming,
        resetStreamingRefs,
        setError,
        finalizeStream,
      };
      await streamSseEvents({
        url: API_ENDPOINTS.CONVERSATION_CHAT_STREAM(convId),
        body: { content: content.trim() },
        signal: startUserTurn(content.trim()),
        onEvent: dispatchSseEvent(chatTurnHandlers(turn, convId)),
        onError: (err) => failStream(turn, err.message),
        onComplete: () => finalizeStream(convId),
      });
    },
    [
      conversationId,
      isStreaming,
      finalizedRef,
      setError,
      startUserTurn,
      appendToken,
      setOptimisticMessages,
      setIsStreaming,
      resetStreamingRefs,
      finalizeStream,
    ],
  );
}

export function useSseChat(options: UseSseChatOptions = {}): UseSseChatReturn {
  const stream = useChatStream(
    SSE_CHAT_USER_ID_PREFIX,
    STREAM_MESSAGE_ID_PREFIX,
  );
  const { optimisticMessages, setOptimisticMessages, isStreaming } = stream;
  const { abortRef, setIsStreaming, resetStreamingRefs } = stream;
  const [error, setError] = useState<string | null>(null);
  const conversationId = options.conversationId ?? null;
  const loadHistory = options.enableHistory !== false;
  const { finalizedRef, finalizeStream } = useFinalizeStream(
    stream,
    loadHistory,
  );
  const historyMessages = useHistory(loadHistory, conversationId);

  const startNewChat = useCallback(() => {
    abortRef.current?.abort();
    setOptimisticMessages([]);
    setIsStreaming(false);
    setError(null);
    resetStreamingRefs();
  }, [abortRef, setOptimisticMessages, setIsStreaming, resetStreamingRefs]);

  const sendMessage = useSendChatMessage({
    stream,
    conversationId,
    isStreaming,
    setError,
    finalizedRef,
    finalizeStream,
  });

  const messages = useMemo(
    () => mergeMessages(historyMessages, optimisticMessages),
    [historyMessages, optimisticMessages],
  );

  return {
    conversationId,
    messages,
    isStreaming,
    error,
    sendMessage,
    startNewChat,
  };
}
