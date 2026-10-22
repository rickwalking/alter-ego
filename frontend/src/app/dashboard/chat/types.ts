/**
 * Chat view hook types (colocated `types.ts`, per the component-type-location
 * convention).
 */

import type { Dispatch, SetStateAction } from "react";
import type { UseSseChatReturn } from "@/modules/conversation";

export interface UseChatSendOptions {
  /** The open conversation, or null to create one on the first send. */
  conversationId: string | null;
  isStreaming: boolean;
  sendMessage: UseSseChatReturn["sendMessage"];
  /** Called with the new id once the first send created the conversation. */
  onConversationCreated: (id: string) => void;
}

export interface UseChatSendReturn {
  input: string;
  setInput: Dispatch<SetStateAction<string>>;
  handleSend: () => Promise<void>;
}
