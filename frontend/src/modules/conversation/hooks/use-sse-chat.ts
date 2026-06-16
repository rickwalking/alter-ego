"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useConversationMessages } from "@/modules/conversation/hooks/use-chat";
import { chatKeys } from "@/modules/conversation/queries";
import { streamSseEvents, SSE_EVENT_TYPE } from "@/lib/sse-client";
import { API_ENDPOINTS } from "@/constants/api";
import type { Message } from "@/schemas/chat";

export interface UseSseChatOptions {
  conversationId?: string | null;
  /** When false, do not load persisted messages (public ephemeral chat). */
  enableHistory?: boolean;
}

export interface UseSseChatReturn {
  conversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  error: string | null;
  sendMessage: (
    content: string,
    overrideConversationId?: string,
  ) => Promise<void>;
  startNewChat: () => void;
}

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

export function useSseChat(options: UseSseChatOptions = {}): UseSseChatReturn {
  const queryClient = useQueryClient();
  const [optimisticMessages, setOptimisticMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamingContentRef = useRef("");
  const streamingMsgIdRef = useRef<string | null>(null);
  const finalizedRef = useRef(false);

  const conversationId = options.conversationId ?? null;

  const loadHistory = options.enableHistory !== false;

  const finalizeStream = useCallback(
    (convId: string) => {
      if (finalizedRef.current) {
        return;
      }
      finalizedRef.current = true;
      setIsStreaming(false);
      streamingContentRef.current = "";
      streamingMsgIdRef.current = null;
      if (!loadHistory) {
        return;
      }
      void queryClient
        .invalidateQueries({ queryKey: chatKeys.messages(convId) })
        .then(() => {
          setOptimisticMessages([]);
        });
    },
    [loadHistory, queryClient],
  );
  const { data: fetchedHistory = [] } = useConversationMessages(
    loadHistory ? conversationId : null,
  );
  const historyMessages = useMemo(
    () => (loadHistory ? fetchedHistory : []),
    [loadHistory, fetchedHistory],
  );

  const startNewChat = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    setOptimisticMessages([]);
    setIsStreaming(false);
    setError(null);
    streamingContentRef.current = "";
    streamingMsgIdRef.current = null;
  }, []);

  const sendMessage = useCallback(
    async (content: string, overrideConversationId?: string) => {
      if (!content.trim() || isStreaming) return;

      const convId = overrideConversationId ?? conversationId;
      if (!convId) return;

      finalizedRef.current = false;
      setError(null);

      const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content: content.trim(),
        sources: [],
        created_at: new Date().toISOString(),
      };
      setOptimisticMessages((prev) => [...prev, userMsg]);

      setIsStreaming(true);
      streamingContentRef.current = "";
      streamingMsgIdRef.current = null;

      if (abortRef.current) {
        abortRef.current.abort();
      }
      abortRef.current = new AbortController();

      await streamSseEvents({
        url: API_ENDPOINTS.CONVERSATION_CHAT_STREAM(convId),
        body: { content: content.trim() },
        signal: abortRef.current.signal,
        onEvent: (event) => {
          const data = event.data;

          if (event.event === SSE_EVENT_TYPE.TOKEN) {
            const tokenContent = (data.content as string) ?? "";
            streamingContentRef.current += tokenContent;
            setOptimisticMessages((prev) => {
              const last = prev[prev.length - 1];
              if (
                last?.role === "assistant" &&
                last.id === streamingMsgIdRef.current
              ) {
                // Accumulate content using the last message's content + new token
                // (ref may have been cleared by COMPLETE event due to React batching)
                return [
                  ...prev.slice(0, -1),
                  { ...last, content: last.content + tokenContent },
                ];
              }
              const newMsg: Message = {
                id: streamingMsgIdRef.current || `stream-${Date.now()}`,
                role: "assistant",
                content:
                  (last?.role === "assistant" ? last.content : "") +
                  tokenContent,
                sources: [],
                created_at: new Date().toISOString(),
              };
              if (!streamingMsgIdRef.current) {
                streamingMsgIdRef.current = newMsg.id;
              }
              return [...prev, newMsg];
            });
            return;
          }

          if (event.event === SSE_EVENT_TYPE.SOURCES) {
            // Backend sends sources in data.content (e.g. {"type":"sources","content":[]})
            const sources = (data.sources || data.content) as
              | Message["sources"]
              | undefined;
            setOptimisticMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant") {
                return [
                  ...prev.slice(0, -1),
                  { ...last, sources: sources ?? [] },
                ];
              }
              return prev;
            });
            return;
          }

          if (event.event === SSE_EVENT_TYPE.COMPLETE) {
            finalizeStream(convId);
            return;
          }

          if (event.event === SSE_EVENT_TYPE.ERROR) {
            const errorContent = (data.content as string) ?? "Unknown error";
            setError(errorContent);
            setIsStreaming(false);
            streamingContentRef.current = "";
            streamingMsgIdRef.current = null;
          }
        },
        onError: (err) => {
          setError(err.message);
          setIsStreaming(false);
          streamingContentRef.current = "";
          streamingMsgIdRef.current = null;
        },
        onComplete: () => {
          finalizeStream(convId);
        },
      });
    },
    [conversationId, finalizeStream, isStreaming],
  );

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
