/**
 * Conversation hook types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), hook contract shapes
 * live here rather than inline in the `use-*.ts` files.
 */

import type { MutableRefObject } from "react";
import type { ChatStream } from "@/lib/use-chat-stream";
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

/** The shared optimistic-message stream state (``useChatStream``). */
export type ChatStreamState = ChatStream;

/** What sending one SSE chat turn needs (AE-0446). */
export interface SendChatDeps {
  stream: ChatStreamState;
  conversationId: string | null;
  isStreaming: boolean;
  setError: (error: string | null) => void;
  finalizedRef: MutableRefObject<boolean>;
  finalizeStream: (convId: string) => void;
}

/** The stable callbacks one streamed chat turn drives (AE-0446). */
export type ChatTurnCallbacks = Pick<
  ChatStreamState,
  | "appendToken"
  | "setOptimisticMessages"
  | "setIsStreaming"
  | "resetStreamingRefs"
> &
  Pick<SendChatDeps, "setError" | "finalizeStream">;
