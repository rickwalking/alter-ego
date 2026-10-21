import type { Dispatch, SetStateAction } from "react";
import type { ChatStream } from "@/lib/use-chat-stream";
/**
 * Distribution hook return/payload types (colocated `types.ts`).
 *
 * Per the component-type-location convention
 * (`frontend/scripts/component-type-location.config.mjs`), hook object shapes
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

/** One slide-1 cover pick at the workflow lock version read. */
export interface CoverPickInput {
  projectId: string;
  assetId: string;
}

/** ``useState`` pair holding the publish chat's conversation id. */
export type ConversationIdState = [
  string | null,
  Dispatch<SetStateAction<string | null>>,
];

/** The stream callbacks one publish-chat turn drives. */
export type PublishTurnCallbacks = Pick<
  ChatStream,
  "appendToken" | "setIsStreaming" | "resetStreamingRefs"
>;

/** What sending one publish-chat turn needs. */
export interface SendPublishDeps {
  projectId: string;
  conversationId: string | null;
  isStreaming: boolean;
  stream: ChatStream;
}
