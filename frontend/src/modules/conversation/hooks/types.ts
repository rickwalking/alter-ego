/**
 * Conversation hook types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), hook contract shapes
 * live here rather than inline in the `use-*.ts` files.
 */

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
