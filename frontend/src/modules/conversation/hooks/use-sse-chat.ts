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
import { classifyChatError, type ChatFailure } from "../chat-errors";
import {
  CHAT_ERROR_KIND,
  CHAT_FAILURE_STAGE,
  CHAT_SEND_RESULT,
  type ChatFailureStage,
  type ChatSendResult,
} from "../constants";
import type {
  ChatStreamState,
  ChatTurnCallbacks,
  ConversationTarget,
  SendChatDeps,
  StreamTurnRequest,
  TurnCallbackDeps,
  TurnOutcome,
  TurnRun,
  UseSseChatOptions,
  UseSseChatReturn,
} from "./types";

const SSE_CHAT_USER_ID_PREFIX = "user-";
const USER_ROLE: Message["role"] = "user";
const STREAM_MESSAGE_ID_PREFIX = "stream-";

export type {
  ConversationTarget,
  UseSseChatOptions,
  UseSseChatReturn,
} from "./types";

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
 * history on, refetch it and then drop the optimistic copies, unless a newer
 * turn (or New chat) started meanwhile: its bubbles must survive the refetch.
 */
function useFinalizeStream(
  stream: ChatStreamState,
  loadHistory: boolean,
): {
  finalizedRef: RefObject<boolean>;
  turnRef: RefObject<number>;
  finalizeStream: (convId: string) => void;
} {
  const queryClient = useQueryClient();
  const finalizedRef = useRef(false);
  const turnRef = useRef(0);
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
      const finishedTurn = turnRef.current;
      void queryClient
        .invalidateQueries({ queryKey: chatKeys.messages(convId) })
        .then(() => {
          if (turnRef.current === finishedTurn) {
            setOptimisticMessages([]);
          }
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
  return { finalizedRef, turnRef, finalizeStream };
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
    [SSE_EVENT_TYPE.ERROR]: () =>
      turn.fail({ kind: CHAT_ERROR_KIND.GENERIC, retryable: false }),
  };
}

/** Drop a trailing user message that never got a reply (a failed turn). */
function dropUnansweredUserTurn(prev: Message[]): Message[] {
  return prev.at(-1)?.role === USER_ROLE ? prev.slice(0, -1) : prev;
}

/** The conversation id, creating the conversation first when needed. */
async function resolveConversationId(
  target: ConversationTarget,
  signal: AbortSignal,
): Promise<string> {
  return typeof target === "function" ? target(signal) : target;
}

/** The callbacks of one turn; ``fail`` records the failure on ``outcome``. */
function turnCallbacks(
  deps: TurnCallbackDeps,
  outcome: TurnOutcome,
): ChatTurnCallbacks {
  const { stream, setError, finalizeStream } = deps;
  return {
    appendToken: stream.appendToken,
    setOptimisticMessages: stream.setOptimisticMessages,
    finalizeStream,
    fail: (failure) => {
      outcome.failed = true;
      setError(failure);
      stream.setIsStreaming(false);
      stream.resetStreamingRefs();
    },
  };
}

function turnResult(outcome: TurnOutcome, signal: AbortSignal): ChatSendResult {
  if (outcome.failed) return CHAT_SEND_RESULT.FAILED;
  if (signal.aborted) return CHAT_SEND_RESULT.IGNORED;
  return CHAT_SEND_RESULT.SENT;
}

/**
 * Request the answer stream and fold its events in. A failure counts as
 * "requesting" until the server answered 200, then as "streaming".
 */
async function streamTurn({
  turn,
  convId,
  content,
  signal,
}: StreamTurnRequest): Promise<void> {
  let stage: ChatFailureStage = CHAT_FAILURE_STAGE.REQUESTING;
  await streamSseEvents({
    url: API_ENDPOINTS.CONVERSATION_CHAT_STREAM(convId),
    body: { content },
    signal,
    onOpen: () => {
      stage = CHAT_FAILURE_STAGE.STREAMING;
    },
    onEvent: dispatchSseEvent(chatTurnHandlers(turn, convId)),
    onError: (err) => turn.fail(classifyChatError(err, stage)),
    onComplete: () => turn.finalizeStream(convId),
  });
}

/** Stream one user turn into the conversation, folding each SSE event in. */
function useRunChatTurn(
  deps: TurnCallbackDeps,
): (run: TurnRun) => Promise<ChatSendResult> {
  const { stream, setError, finalizedRef, turnRef, finalizeStream } = deps;
  const { startUserTurn, setOptimisticMessages } = stream;
  return useCallback(
    async ({ content, target }: TurnRun) => {
      const outcome: TurnOutcome = { failed: false };
      const turn = turnCallbacks(
        { stream, setError, finalizedRef, turnRef, finalizeStream },
        outcome,
      );
      turnRef.current += 1;
      finalizedRef.current = false;
      setError(null);
      setOptimisticMessages(dropUnansweredUserTurn);
      const signal = startUserTurn(content);
      let convId: string;
      try {
        convId = await resolveConversationId(target, signal);
      } catch (error) {
        if (signal.aborted) return CHAT_SEND_RESULT.IGNORED;
        turn.fail(classifyChatError(error, CHAT_FAILURE_STAGE.CREATING));
        return CHAT_SEND_RESULT.FAILED;
      }
      if (signal.aborted) return CHAT_SEND_RESULT.IGNORED;
      await streamTurn({ turn, convId, content, signal });
      return turnResult(outcome, signal);
    },
    [
      stream,
      finalizedRef,
      turnRef,
      setError,
      startUserTurn,
      setOptimisticMessages,
      finalizeStream,
    ],
  );
}

/**
 * Send one turn at a time: a second send while one is in flight is ignored.
 * ``isBusy`` answers synchronously, so a caller can check before it clears
 * the composer.
 */
function useSendChatMessage(
  deps: SendChatDeps,
): Pick<UseSseChatReturn, "sendMessage" | "isBusy"> {
  const { conversationId } = deps;
  const inFlightRef = useRef(false);
  const runTurn = useRunChatTurn(deps);
  const isBusy = useCallback(() => inFlightRef.current, []);
  const sendMessage = useCallback(
    async (content: string, target?: ConversationTarget | null) => {
      const trimmed = content.trim();
      const resolved = target ?? conversationId;
      if (!trimmed || !resolved || inFlightRef.current) {
        return CHAT_SEND_RESULT.IGNORED;
      }
      inFlightRef.current = true;
      try {
        return await runTurn({ content: trimmed, target: resolved });
      } finally {
        inFlightRef.current = false;
      }
    },
    [conversationId, runTurn],
  );
  return { sendMessage, isBusy };
}

/** Abort the turn in flight and clear the chat (stale refetches see a new turn). */
function useStartNewChat(
  stream: ChatStreamState,
  turnRef: RefObject<number>,
  setError: SendChatDeps["setError"],
): () => void {
  const { abortRef, setOptimisticMessages, setIsStreaming } = stream;
  const { resetStreamingRefs } = stream;
  return useCallback(() => {
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
  ]);
}

export function useSseChat(options: UseSseChatOptions = {}): UseSseChatReturn {
  const stream = useChatStream(
    SSE_CHAT_USER_ID_PREFIX,
    STREAM_MESSAGE_ID_PREFIX,
  );
  const { optimisticMessages, isStreaming } = stream;
  const [failure, setError] = useState<ChatFailure | null>(null);
  const conversationId = options.conversationId ?? null;
  const loadHistory = options.enableHistory !== false;
  const { finalizedRef, turnRef, finalizeStream } = useFinalizeStream(
    stream,
    loadHistory,
  );
  const historyMessages = useHistory(loadHistory, conversationId);

  const startNewChat = useStartNewChat(stream, turnRef, setError);

  const { sendMessage, isBusy } = useSendChatMessage({
    stream,
    conversationId,
    setError,
    finalizedRef,
    turnRef,
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
    error: failure?.kind ?? null,
    canRetry: failure?.retryable ?? false,
    sendMessage,
    isBusy,
    startNewChat,
  };
}
