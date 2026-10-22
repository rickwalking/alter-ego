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
import type { ChatSendResult } from "../constants";

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
  error: string | null;
  /**
   * Send one turn. The user bubble and the typing state show at once, even
   * while ``target`` is still creating the conversation; a second call while a
   * turn is in flight is ignored.
   */
  sendMessage: (
    content: string,
    target?: ConversationTarget | null,
  ) => Promise<ChatSendResult>;
  startNewChat: () => void;
}

/** The shared optimistic-message stream state (``useChatStream``). */
export type ChatStreamState = ChatStream;

/** What sending one SSE chat turn needs. */
export interface SendChatDeps {
  stream: ChatStreamState;
  conversationId: string | null;
  setError: (error: string | null) => void;
  finalizedRef: RefObject<boolean>;
  /** Bumped by every new turn and by New chat; stale refetches compare it. */
  turnRef: RefObject<number>;
  finalizeStream: (convId: string) => void;
}

/** The stable callbacks one streamed chat turn drives. */
export type ChatTurnCallbacks = Pick<
  ChatStreamState,
  "appendToken" | "setOptimisticMessages"
> &
  Pick<SendChatDeps, "finalizeStream"> & {
    /** Show ``message``, end the stream and mark the turn as failed. */
    fail: (message: string) => void;
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
