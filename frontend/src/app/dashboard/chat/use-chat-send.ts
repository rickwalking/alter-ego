"use client";

import { useCallback, useRef, useState } from "react";
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
 * A creator for ``sendMessage``: makes the Alter-Ego conversation and opens it,
 * unless New chat abandoned the turn meanwhile (its signal is aborted).
 */
function useConversationCreator(
  onConversationCreated: (id: string) => void,
): (signal: AbortSignal) => Promise<string> {
  const { mutateAsync: createConversation } = useCreateConversation();

  return useCallback(
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
}

/**
 * The composer text and the send action shared by the public and dashboard
 * chats. The composer clears at once; the conversation is created inside the
 * send (so the bubble shows while it is pending); a failed send gives the text
 * back unless the user already typed something new, and ``retry`` sends it again.
 */
export function useChatSend({
  conversationId,
  isStreaming,
  sendMessage,
  isBusy,
  onConversationCreated,
}: UseChatSendOptions): UseChatSendReturn {
  const [input, setInput] = useState("");
  const createAndOpenConversation = useConversationCreator(
    onConversationCreated,
  );

  const lastFailedRef = useRef<string | null>(null);

  const send = useCallback(
    async (content: string) => {
      lastFailedRef.current = null;
      const result = await sendMessage(
        content,
        conversationId ?? createAndOpenConversation,
      );
      if (result !== CHAT_SEND_RESULT.FAILED) return;
      lastFailedRef.current = content;
      setInput((current) => current || content);
    },
    [conversationId, createAndOpenConversation, sendMessage],
  );

  const handleSend = useCallback(async () => {
    const content = input.trim();
    if (!content || isStreaming || isBusy()) return;
    setInput("");
    await send(content);
  }, [input, isStreaming, isBusy, send]);

  const sendNow = useCallback(
    async (text: string) => {
      if (isStreaming || isBusy()) return;
      await send(text);
    },
    [isStreaming, isBusy, send],
  );

  const retry = useCallback(async () => {
    const content = lastFailedRef.current;
    if (!content || isStreaming || isBusy()) return;
    setInput((current) => (current.trim() === content ? "" : current));
    await send(content);
  }, [isStreaming, isBusy, send]);

  const forgetFailed = useCallback(() => {
    lastFailedRef.current = null;
  }, []);

  return { input, setInput, handleSend, retry, forgetFailed, sendNow };
}
