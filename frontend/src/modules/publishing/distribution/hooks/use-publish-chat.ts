"use client";

import { useCallback, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useCreateConversation,
  useConversationMessages,
  useConversation,
} from "@/modules/conversation";
import { ApiError } from "@/lib/api-client";
import { streamSseEvents, SSE_EVENT_TYPE } from "@/lib/sse-client";
import { API_ENDPOINTS } from "@/constants/api";
import type { Message } from "@/schemas/chat";
import {
  PUBLISH_CHAT_STORAGE_KEY,
  MESSAGE_ROLE_USER,
  MESSAGE_ROLE_ASSISTANT,
  OPTIMISTIC_MESSAGE_ID_PREFIX,
  STREAM_MESSAGE_ID_PREFIX,
  CONVERSATION_TITLE_PREFIX,
  CONVERSATION_METADATA_PROJECT_ID,
  TOOL_REFINE_CAROUSEL_COPY,
} from "@/constants/publish-chat";
import { carouselKeys } from "@/modules/carousel-presentation";

export interface UsePublishChatReturn {
  conversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  sendMessage: (content: string) => void;
}

function readStoredConversationId(projectId: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(PUBLISH_CHAT_STORAGE_KEY(projectId));
  } catch {
    return null;
  }
}

function buildContextPrefix(projectId: string): string {
  return `(carousel project_id=${projectId}) `;
}

export function usePublishChat(projectId: string): UsePublishChatReturn {
  const queryClient = useQueryClient();
  const createConversation = useCreateConversation();
  const [conversationId, setConversationId] = useState<string | null>(() =>
    readStoredConversationId(projectId),
  );
  const [optimisticMessages, setOptimisticMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const streamingContentRef = useRef("");
  const streamingMsgIdRef = useRef<string | null>(null);
  const creatingRef = useRef(false);

  const { data: historyMessages = [], error: historyError } =
    useConversationMessages(conversationId);

  const { data: conversation } = useConversation(conversationId);

  // Create a new conversation when no stored ID exists.
  useLayoutEffect(() => {
    if (!projectId || conversationId || creatingRef.current) return;

    creatingRef.current = true;
    createConversation
      .mutateAsync({
        title: `${CONVERSATION_TITLE_PREFIX}${projectId}`,
        metadata: { [CONVERSATION_METADATA_PROJECT_ID]: projectId },
      })
      .then((conv) => {
        localStorage.setItem(PUBLISH_CHAT_STORAGE_KEY(projectId), conv.id);
        setConversationId(conv.id);
      })
      .catch(() => {
        // Silently ignore creation errors (e.g. 429 rate-limit).
      })
      .finally(() => {
        creatingRef.current = false;
      });
  }, [projectId, conversationId, createConversation]);

  // Handle invalid or mismatched conversation IDs.
  useLayoutEffect(() => {
    if (!conversationId || !projectId) return;

    const isNotFound =
      historyError instanceof ApiError && historyError.status === 404;

    const metadataProjectId =
      conversation?.metadata &&
      typeof conversation.metadata === "object" &&
      CONVERSATION_METADATA_PROJECT_ID in conversation.metadata
        ? String(
            (conversation.metadata as Record<string, unknown>)[
              CONVERSATION_METADATA_PROJECT_ID
            ],
          )
        : null;

    const isMismatched =
      metadataProjectId !== null && metadataProjectId !== projectId;

    if (!isNotFound && !isMismatched) return;

    localStorage.removeItem(PUBLISH_CHAT_STORAGE_KEY(projectId));

    const timer = setTimeout(() => {
      setConversationId(null);
    }, 0);

    return () => {
      clearTimeout(timer);
    };
  }, [conversationId, projectId, historyError, conversation]);

  const sendMessage = useCallback(
    (content: string) => {
      if (!content.trim() || !conversationId || isStreaming) {
        return;
      }

      const userMsg: Message = {
        id: `${OPTIMISTIC_MESSAGE_ID_PREFIX}${Date.now()}`,
        role: MESSAGE_ROLE_USER,
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

      const payload = buildContextPrefix(projectId) + content.trim();

      streamSseEvents({
        url: API_ENDPOINTS.CONVERSATION_PUBLISH_CHAT_STREAM(conversationId),
        body: { content: payload },
        signal: abortRef.current.signal,
        onEvent: (event) => {
          const data = event.data;

          if (event.event === SSE_EVENT_TYPE.TOOL_RESULT) {
            const tool = data.tool as string | undefined;
            if (tool === TOOL_REFINE_CAROUSEL_COPY) {
              queryClient.invalidateQueries({
                queryKey: carouselKeys.detail(projectId),
              });
            }
            return;
          }

          if (event.event === SSE_EVENT_TYPE.TOKEN) {
            const tokenContent = (data.content as string) ?? "";
            streamingContentRef.current += tokenContent;
            setOptimisticMessages((prev) => {
              const last = prev[prev.length - 1];
              if (
                last?.role === MESSAGE_ROLE_ASSISTANT &&
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
                id:
                  streamingMsgIdRef.current ||
                  `${STREAM_MESSAGE_ID_PREFIX}${Date.now()}`,
                role: MESSAGE_ROLE_ASSISTANT,
                content: streamingContentRef.current,
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

          if (event.event === SSE_EVENT_TYPE.COMPLETE) {
            setIsStreaming(false);
            streamingContentRef.current = "";
            streamingMsgIdRef.current = null;
            return;
          }

          if (event.event === SSE_EVENT_TYPE.ERROR) {
            setIsStreaming(false);
            streamingContentRef.current = "";
            streamingMsgIdRef.current = null;
          }
        },
        onError: () => {
          setIsStreaming(false);
          streamingContentRef.current = "";
          streamingMsgIdRef.current = null;
        },
        onComplete: () => {
          setIsStreaming(false);
        },
      });
    },
    [conversationId, projectId, isStreaming, queryClient],
  );

  // Cleanup abort controller on unmount.
  useLayoutEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, []);

  const messages = useMemo(
    () => [...historyMessages, ...optimisticMessages],
    [historyMessages, optimisticMessages],
  );

  return { conversationId, messages, isStreaming, sendMessage };
}
