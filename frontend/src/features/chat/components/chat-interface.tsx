"use client";

import { useState, useCallback, useMemo } from "react";
import {
  useConversations,
  useConversationMessages,
  useCreateConversation,
  useSendMessage,
} from "../hooks/use-chat";
import { type Message } from "@/schemas/chat";
import { MessageList } from "./message-list";
import { MessageInput } from "./message-input";
import { ConversationSidebar } from "./conversation-sidebar";

export function ChatInterface() {
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isComposingNewChat, setIsComposingNewChat] = useState(false);
  const [optimisticMessages, setOptimisticMessages] = useState<Message[]>([]);

  const { data: conversations = [], isLoading: loadingConversations } = useConversations();
  const effectiveConversationId = useMemo(
    () =>
      isComposingNewChat
        ? null
        : activeConversationId ?? (conversations.length > 0 ? conversations[0].id : null),
    [activeConversationId, conversations, isComposingNewChat],
  );
  const { data: messages = [], isLoading: loadingMessages } = useConversationMessages(effectiveConversationId);
  const createConversation = useCreateConversation();
  const sendMessage = useSendMessage();

  const isLoading = sendMessage.isPending || loadingMessages;
  const displayMessages = [...messages, ...optimisticMessages];

  const handleSendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    let convId = effectiveConversationId;

    if (!convId) {
      const newConv = await createConversation.mutateAsync({});
      convId = newConv.id;
      setActiveConversationId(convId);
      setIsComposingNewChat(false);
    }

    const optimisticMsg: Message = {
      id: `opt-${Date.now()}`,
      role: "user",
      content,
      sources: [],
      created_at: new Date().toISOString(),
    };
    setOptimisticMessages((prev) => [...prev, optimisticMsg]);

    try {
      const response = await sendMessage.mutateAsync({ conversationId: convId, content });

      const assistantMsg: Message = {
        id: `opt-res-${Date.now()}`,
        role: "assistant",
        content: response.content,
        sources: response.sources,
        created_at: new Date().toISOString(),
      };
      setOptimisticMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setOptimisticMessages((prev) => prev.filter((m) => m.id !== optimisticMsg.id));
    }
  }, [effectiveConversationId, createConversation, sendMessage]);

  const handleNewChat = useCallback(() => {
    setActiveConversationId(null);
    setIsComposingNewChat(true);
    setOptimisticMessages([]);
  }, []);

  const handleSelectConversation = useCallback((id: string) => {
    setActiveConversationId(id);
    setIsComposingNewChat(false);
    setOptimisticMessages([]);
  }, []);

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
          <MessageList messages={displayMessages} />
        </div>
        <MessageInput
          onSend={handleSendMessage}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}
