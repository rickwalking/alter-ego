"use client";

import {
  useCallback,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useCreateConversation,
  useConversationMessages,
  useConversation,
} from "@/features/chat/hooks/use-chat";
import { ApiError } from "@/lib/api-client";
import type { Message } from "@/schemas/chat";
import {
  PUBLISH_CHAT_STORAGE_KEY,
  WS_PROTOCOL_SECURE,
  WS_PROTOCOL_INSECURE,
  WS_MESSAGE_TYPE_TOKEN,
  WS_MESSAGE_TYPE_COMPLETE,
  WS_MESSAGE_TYPE_ERROR,
  WS_MESSAGE_TYPE_TOOL_RESULT,
  TOOL_REFINE_CAROUSEL_COPY,
  MESSAGE_ROLE_USER,
  MESSAGE_ROLE_ASSISTANT,
  OPTIMISTIC_MESSAGE_ID_PREFIX,
  STREAM_MESSAGE_ID_PREFIX,
  CONVERSATION_TITLE_PREFIX,
  CONVERSATION_METADATA_PROJECT_ID,
} from "@/constants/publish-chat";
import { carouselKeys } from "@/features/carousel/queries";

export interface UsePublishChatReturn {
  conversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  sendMessage: (content: string) => void;
}

function getWsProtocol(): string {
  return window.location.protocol === "https:" ? WS_PROTOCOL_SECURE : WS_PROTOCOL_INSECURE;
}

function buildWsUrl(conversationId: string): string {
  return `${getWsProtocol()}//${window.location.host}/ws/chat/${conversationId}`;
}

function buildContextPrefix(projectId: string): string {
  return `(carousel project_id=${projectId}) `;
}

function readStoredConversationId(projectId: string): string | null {
  return localStorage.getItem(PUBLISH_CHAT_STORAGE_KEY(projectId));
}

export function usePublishChat(projectId: string): UsePublishChatReturn {
  const queryClient = useQueryClient();
  const createConversation = useCreateConversation();
  const [conversationId, setConversationId] = useState<string | null>(() =>
    readStoredConversationId(projectId),
  );
  const [optimisticMessages, setOptimisticMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const streamingContentRef = useRef("");
  const streamingMsgIdRef = useRef<string | null>(null);
  const creatingRef = useRef(false);

  const {
    data: historyMessages = [],
    error: historyError,
  } = useConversationMessages(conversationId);

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

  // WebSocket connection for streaming chat.
  useLayoutEffect(() => {
    if (!conversationId) return;

    streamingContentRef.current = "";
    streamingMsgIdRef.current = null;

    const socket = new WebSocket(buildWsUrl(conversationId));

    socket.onopen = () => {
      setOptimisticMessages([]);
      setIsStreaming(false);
    };

    socket.onclose = () => {
      setIsStreaming(false);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as Record<string, unknown>;

        if (data.type === WS_MESSAGE_TYPE_TOOL_RESULT) {
          const toolResult = data as { tool?: string };
          if (toolResult.tool === TOOL_REFINE_CAROUSEL_COPY) {
            queryClient.invalidateQueries({
              queryKey: carouselKeys.detail(projectId),
            });
          }
          return;
        }

        if (data.type === WS_MESSAGE_TYPE_TOKEN) {
          const tokenData = data as { content?: string };
          streamingContentRef.current += tokenData.content ?? "";
          setOptimisticMessages((prev) => {
            const last = prev[prev.length - 1];
            if (
              last?.role === MESSAGE_ROLE_ASSISTANT &&
              last.id === streamingMsgIdRef.current
            ) {
              return [
                ...prev.slice(0, -1),
                { ...last, content: streamingContentRef.current },
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

        if (data.type === WS_MESSAGE_TYPE_COMPLETE) {
          setIsStreaming(false);
          streamingContentRef.current = "";
          streamingMsgIdRef.current = null;
          return;
        }

        if (data.type === WS_MESSAGE_TYPE_ERROR) {
          setIsStreaming(false);
          streamingContentRef.current = "";
          streamingMsgIdRef.current = null;
        }
      } catch {
        // Ignore parse errors.
      }
    };

    wsRef.current = socket;
    return () => {
      socket.close();
      wsRef.current = null;
    };
  }, [conversationId, projectId, queryClient]);

  const sendMessage = useCallback(
    (content: string) => {
      if (!content.trim() || wsRef.current?.readyState !== WebSocket.OPEN) {
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

      const payload = buildContextPrefix(projectId) + content.trim();
      wsRef.current.send(JSON.stringify({ content: payload }));
      setIsStreaming(true);
      streamingMsgIdRef.current = null;
      streamingContentRef.current = "";
    },
    [projectId],
  );

  const messages = useMemo(
    () => [...historyMessages, ...optimisticMessages],
    [historyMessages, optimisticMessages],
  );

  return { conversationId, messages, isStreaming, sendMessage };
}
