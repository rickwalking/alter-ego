"use client";

import { useState, useCallback, useMemo } from "react";
import { useConversations, useCreateConversation } from "../hooks/use-chat";
import { useSseChat } from "../hooks/use-sse-chat";
import {
  AGENT_ORIGIN_ALTER_EGO,
  CONVERSATION_METADATA_AGENT_ORIGIN,
} from "@/constants/publish-chat";
import { MessageList } from "./message-list";
import { MessageInput } from "./message-input";
import { ConversationSidebar } from "./conversation-sidebar";

export function ChatInterface() {
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null);
  const [isComposingNewChat, setIsComposingNewChat] = useState(false);

  const { data: conversations = [], isLoading: loadingConversations } =
    useConversations();
  const createConversation = useCreateConversation();

  const effectiveConversationId = useMemo(
    () =>
      isComposingNewChat
        ? null
        : (activeConversationId ??
          (conversations.length > 0 ? conversations[0].id : null)),
    [activeConversationId, conversations, isComposingNewChat],
  );

  const {
    conversationId: sseConversationId,
    messages: sseMessages,
    isStreaming,
    error: sseError,
    sendMessage: sendSseMessage,
    startNewChat: startSseNewChat,
  } = useSseChat({ conversationId: effectiveConversationId });

  const handleSendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      // Create a conversation when none is selected (new chat or first message).
      let convId = effectiveConversationId;
      if (!convId) {
        const newConv = await createConversation.mutateAsync({
          metadata: {
            [CONVERSATION_METADATA_AGENT_ORIGIN]: AGENT_ORIGIN_ALTER_EGO,
          },
        });
        convId = newConv.id;
        setActiveConversationId(convId);
        setIsComposingNewChat(false);
      }

      await sendSseMessage(content, convId);
    },
    [effectiveConversationId, createConversation, sendSseMessage],
  );

  const handleNewChat = useCallback(() => {
    setActiveConversationId(null);
    setIsComposingNewChat(true);
    startSseNewChat();
  }, [startSseNewChat]);

  const handleSelectConversation = useCallback(
    (id: string) => {
      setActiveConversationId(id);
      setIsComposingNewChat(false);
      startSseNewChat();
    },
    [startSseNewChat],
  );

  const displayConversationId = sseConversationId ?? effectiveConversationId;
  const isLoading = isStreaming;

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      <ConversationSidebar
        conversations={conversations}
        activeId={effectiveConversationId}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        isLoading={loadingConversations}
      />
      <div className="flex flex-1 flex-col">
        <div className="flex-1 overflow-auto">
          <MessageList messages={sseMessages} isStreaming={isStreaming} />
        </div>
        {sseError && (
          <div className="border-t border-destructive/20 bg-destructive/10 px-4 py-2 text-destructive text-sm">
            {sseError}
          </div>
        )}
        <MessageInput onSend={handleSendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
}
