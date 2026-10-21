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
import { useChatStream } from "@/lib/use-chat-stream";
import {
  dispatchSseEvent,
  sseContentText,
  type SseEventHandlers,
} from "@/lib/sse-event-data";
import { API_ENDPOINTS, HTTP_STATUS } from "@/constants/api";
import {
  PUBLISH_CHAT_STORAGE_KEY,
  OPTIMISTIC_MESSAGE_ID_PREFIX,
  STREAM_MESSAGE_ID_PREFIX,
  CONVERSATION_TITLE_PREFIX,
  CONVERSATION_METADATA_PROJECT_ID,
  TOOL_REFINE_CAROUSEL_COPY,
} from "@/constants/publish-chat";
import { carouselKeys } from "@/modules/carousel-presentation";
import type {
  ConversationIdState,
  PublishTurnCallbacks,
  SendPublishDeps,
  UsePublishChatReturn,
} from "./types";

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

/** The project id a conversation was created for (null when untagged). */
function conversationProjectId(metadata: unknown): string | null {
  if (
    !metadata ||
    typeof metadata !== "object" ||
    !(CONVERSATION_METADATA_PROJECT_ID in metadata)
  ) {
    return null;
  }
  return String(
    (metadata as Record<string, unknown>)[CONVERSATION_METADATA_PROJECT_ID],
  );
}

/** Create (and remember) a conversation when none is stored for the project. */
function useEnsureConversation(
  projectId: string,
  [conversationId, setConversationId]: ConversationIdState,
): void {
  const createConversation = useCreateConversation();
  const creatingRef = useRef(false);
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
  }, [projectId, conversationId, createConversation, setConversationId]);
}

/** Forget a stored conversation that is gone (404) or belongs elsewhere. */
function useDropStaleConversation(
  projectId: string,
  [conversationId, setConversationId]: ConversationIdState,
  historyError: unknown,
): void {
  const { data: conversation } = useConversation(conversationId);
  useLayoutEffect(() => {
    if (!conversationId || !projectId) return;

    const isNotFound =
      historyError instanceof ApiError &&
      historyError.status === HTTP_STATUS.NOT_FOUND;
    const metadataProjectId = conversationProjectId(conversation?.metadata);
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
  }, [
    conversationId,
    projectId,
    historyError,
    conversation,
    setConversationId,
  ]);
}

/** The SSE handlers of one publish-chat turn. */
function publishTurnHandlers(
  { appendToken, setIsStreaming, resetStreamingRefs }: PublishTurnCallbacks,
  onCarouselRefined: () => void,
): SseEventHandlers {
  const endStream = (): void => {
    setIsStreaming(false);
    resetStreamingRefs();
  };
  return {
    [SSE_EVENT_TYPE.TOOL_RESULT]: (data) => {
      if (data.tool === TOOL_REFINE_CAROUSEL_COPY) {
        onCarouselRefined();
      }
    },
    [SSE_EVENT_TYPE.TOKEN]: (data) => appendToken(sseContentText(data, "")),
    [SSE_EVENT_TYPE.COMPLETE]: endStream,
    [SSE_EVENT_TYPE.ERROR]: endStream,
  };
}

/** Stream one publish-chat turn (the project id is sent as context). */
function useSendPublishMessage({
  projectId,
  conversationId,
  isStreaming,
  stream,
}: SendPublishDeps): UsePublishChatReturn["sendMessage"] {
  const queryClient = useQueryClient();
  const { startUserTurn, appendToken, setIsStreaming, resetStreamingRefs } =
    stream;
  return useCallback(
    (content: string) => {
      if (!content.trim() || !conversationId || isStreaming) {
        return;
      }
      const signal = startUserTurn(content.trim());
      const turn = { appendToken, setIsStreaming, resetStreamingRefs };
      const refreshCarousel = (): void => {
        void queryClient.invalidateQueries({
          queryKey: carouselKeys.detail(projectId),
        });
      };
      void streamSseEvents({
        url: API_ENDPOINTS.CONVERSATION_PUBLISH_CHAT_STREAM(conversationId),
        body: { content: buildContextPrefix(projectId) + content.trim() },
        signal,
        onEvent: dispatchSseEvent(publishTurnHandlers(turn, refreshCarousel)),
        onError: () => {
          setIsStreaming(false);
          resetStreamingRefs();
        },
        onComplete: () => {
          setIsStreaming(false);
        },
      });
    },
    [
      conversationId,
      projectId,
      isStreaming,
      queryClient,
      startUserTurn,
      appendToken,
      setIsStreaming,
      resetStreamingRefs,
    ],
  );
}

export function usePublishChat(projectId: string): UsePublishChatReturn {
  const conversationIdState = useState<string | null>(() =>
    readStoredConversationId(projectId),
  );
  const [conversationId] = conversationIdState;
  const stream = useChatStream(
    OPTIMISTIC_MESSAGE_ID_PREFIX,
    STREAM_MESSAGE_ID_PREFIX,
  );
  const { optimisticMessages, isStreaming } = stream;
  const { data: historyMessages = [], error: historyError } =
    useConversationMessages(conversationId);
  useEnsureConversation(projectId, conversationIdState);
  useDropStaleConversation(projectId, conversationIdState, historyError);

  const sendMessage = useSendPublishMessage({
    projectId,
    conversationId,
    isStreaming,
    stream,
  });

  const messages = useMemo(
    () => [...historyMessages, ...optimisticMessages],
    [historyMessages, optimisticMessages],
  );

  return { conversationId, messages, isStreaming, sendMessage };
}
