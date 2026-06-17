/**
 * Distribution hook return/payload types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), hook object shapes
 * live here rather than inline in the `use-*.ts` files.
 */

import type { Message } from "@/schemas/chat";

export interface UsePublishChatReturn {
  conversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  sendMessage: (content: string) => void;
}

export interface InstagramPublishPayload {
  projectId: string;
  caption: string;
}
