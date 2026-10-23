/**
 * Conversation hook types (colocated `types.ts`).
 *
 * Per the component-type-location convention (
 * `frontend/scripts/component-type-location.config.mjs`), hook contract shapes
 * live here rather than inline in the `use-*.ts` files.
 */

import type { RefObject } from "react";
import type { ChatStream } from "@/lib/use-chat-stream";
import type { Message } from "@/schemas/chat";
import type { ChatFailure } from "../chat-errors";
import type { ChatErrorKind, ChatSendResult } from "../constants";

/**
 * The conversation to send into: its id, or a function that creates it. The
 * creator gets the turn's signal: when it is aborted (New chat while creating)
 * the created conversation must not be opened.
 */
export type ConversationTarget =
  | string
  | ((signal: AbortSignal) => Promise<string>);

export interface UseSseChatOptions {
  conversationId?: string | null;
  /** When false, do not load persisted messages (public ephemeral chat). */
  enableHistory?: boolean;
}

export interface UseSseChatReturn {
  conversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  /** The history ends with a message whose reply the server is still writing. */
  awaitingReply: boolean;
  /** What went wrong with the last turn, or null. */
  error: ChatErrorKind | null;
  /** Whether Try again can help: nothing was saved yet (no answer had started). */
  canRetry: boolean;
  /**
   * Send one turn. The user bubble and the typing state show at once, even
   * while ``target`` is still creating the conversation; a second call while a
   * turn is in flight is ignored.
   */
  sendMessage: (
    content: string,
    target?: ConversationTarget | null,
  ) => Promise<ChatSendResult>;
  /** Whether a turn is in flight right now (``sendMessage`` would ignore a send). */
  isBusy: () => boolean;
  startNewChat: () => void;
  /** Stop the reply in flight; the text that already arrived stays. */
  stopStreaming: () => void;
}

/** The shared optimistic-message stream state (``useChatStream``). */
export type ChatStreamState = ChatStream;

/** What sending one SSE chat turn needs. */
export interface SendChatDeps {
  stream: ChatStreamState;
  conversationId: string | null;
  setError: (failure: ChatFailure | null) => void;
  finalizedRef: RefObject<boolean>;
  /** Bumped by every new turn and by New chat; stale refetches compare it. */
  turnRef: RefObject<number>;
  finalizeStream: (convId: string) => void;
  /**
   * History is on: a new turn starts from it, dropping the optimistic copies
   * an earlier stopped or failed turn left behind.
   */
  loadHistory: boolean;
}

/** The stable callbacks one streamed chat turn drives. */
export type ChatTurnCallbacks = Pick<
  ChatStreamState,
  "appendToken" | "setOptimisticMessages"
> &
  Pick<SendChatDeps, "finalizeStream"> & {
    /** Show the failure, end the stream and mark the turn as failed. */
    fail: (failure: ChatFailure) => void;
  };

/** What running one turn needs (the conversation id arrives with the turn). */
export type TurnCallbackDeps = Omit<SendChatDeps, "conversationId">;

/** One turn's text and the conversation it goes into. */
export interface TurnRun {
  content: string;
  target: ConversationTarget;
}

/** Whether a turn failed (set from inside the stream callbacks). */
export interface TurnOutcome {
  failed: boolean;
}

/** One answer-stream request of a turn. */
export interface StreamTurnRequest {
  turn: ChatTurnCallbacks;
  convId: string;
  content: string;
  signal: AbortSignal;
}

/** What `useTurnMessages` merges, and the send it wraps. */
export interface TurnMessagesInput {
  historyMessages: Message[];
  optimisticMessages: Message[];
  isStreaming: boolean;
  sendTurn: UseSseChatReturn["sendMessage"];
  isBusy: () => boolean;
}
