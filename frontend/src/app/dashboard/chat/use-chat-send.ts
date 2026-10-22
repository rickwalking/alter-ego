"use client";

import { useCallback, useState } from "react";
import {
  AGENT_ORIGIN_ALTER_EGO,
  CONVERSATION_METADATA_AGENT_ORIGIN,
} from "@/constants/publish-chat";
import {
  CHAT_SEND_RESULT,
  useCreateConversation,
} from "@/modules/conversation";
import type { UseChatSendOptions, UseChatSendReturn } from "./types";

/**
 * The composer text and the send action shared by the public and dashboard
 * chats. The composer clears at once; the conversation is created inside the
 * send (so the bubble shows while it is pending); a failed send gives the text
 * back unless the user already typed something new.
 */
export function useChatSend({
  conversationId,
  isStreaming,
  sendMessage,
  onConversationCreated,
}: UseChatSendOptions): UseChatSendReturn {
  const [input, setInput] = useState("");
  const { mutateAsync: createConversation } = useCreateConversation();

  const createAndOpenConversation = useCallback(
    async (signal: AbortSignal) => {
      const created = await createConversation({
        metadata: {
          [CONVERSATION_METADATA_AGENT_ORIGIN]: AGENT_ORIGIN_ALTER_EGO,
        },
      });
      if (!signal.aborted) {
        onConversationCreated(created.id);
      }
      return created.id;
    },
    [createConversation, onConversationCreated],
  );

  const handleSend = useCallback(async () => {
    const content = input.trim();
    if (!content || isStreaming) return;
    setInput("");
    const result = await sendMessage(
      content,
      conversationId ?? createAndOpenConversation,
    );
    if (result === CHAT_SEND_RESULT.FAILED) {
      setInput((current) => current || content);
    }
  }, [
    input,
    isStreaming,
    conversationId,
    createAndOpenConversation,
    sendMessage,
  ]);

  return { input, setInput, handleSend };
}
