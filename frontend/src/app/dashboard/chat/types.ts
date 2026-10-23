/**
 * Chat view hook types (colocated `types.ts`, per the component-type-location
 * convention).
 */

import type { Dispatch, SetStateAction } from "react";
import type { ChatErrorKind, UseSseChatReturn } from "@/modules/conversation";

export interface UseChatSendOptions {
  /** The open conversation, or null to create one on the first send. */
  conversationId: string | null;
  isStreaming: boolean;
  sendMessage: UseSseChatReturn["sendMessage"];
  /** A turn is in flight: a send now would be ignored, so keep the text. */
  isBusy: UseSseChatReturn["isBusy"];
  /** Called with the new id once the first send created the conversation. */
  onConversationCreated: (id: string) => void;
}

export interface UseChatSendReturn {
  input: string;
  setInput: Dispatch<SetStateAction<string>>;
  handleSend: () => Promise<void>;
  /** Send the last failed message again. */
  retry: () => Promise<void>;
  /** Forget the failed message (New chat). */
  forgetFailed: () => void;
  /** Send ``text`` right away (a suggested question), leaving the composer alone. */
  sendNow: (text: string) => Promise<void>;
}

export interface ChatErrorBannerProps {
  kind: ChatErrorKind;
  /** Where to come back to after signing in again. */
  loginRedirect?: string;
  /** Nothing was saved yet, so Try again is offered. */
  canRetry?: boolean;
  onRetry: () => void;
  /** Always offered when given: the way out of a full or gone conversation. */
  onNewChat?: () => void;
}
