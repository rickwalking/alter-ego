"use client";

import { useCallback, useMemo, useState } from "react";
import { useLocale } from "next-intl";
import { useConversations, useSseChat } from "@/modules/conversation";
import {
  mapConversationToDashboard,
  mapMessageToDashboard,
} from "@/modules/editorial-operations";
import {
  DASHBOARD_CHAT_BG_DEEP,
  DASHBOARD_CHAT_BG_OVERLAY_LIGHT,
} from "@/modules/editorial-operations";
import { ChatComposer } from "@/app/dashboard/chat/chat-composer";
import { ChatHeader } from "@/app/dashboard/chat/chat-header";
import { ChatMessageList } from "@/app/dashboard/chat/chat-message-list";
import { ChatSidebar } from "@/app/dashboard/chat/chat-sidebar";
import { useChatSend } from "@/app/dashboard/chat/use-chat-send";
import { useOffCanvas } from "@/lib/use-off-canvas";

const CHAT_CONVERSATIONS_ID = "chat-conversations";

export function DashboardChatView(): React.ReactElement {
  const [activeConv, setActiveConv] = useState<string | null>(null);
  const locale = useLocale();
  const [isComposingNew, setIsComposingNew] = useState(false);
  const convDrawer = useOffCanvas();

  const { data: conversations = [] } = useConversations();

  const effectiveConvId = useMemo(
    () =>
      isComposingNew ? null : (activeConv ?? conversations[0]?.id ?? null),
    [activeConv, conversations, isComposingNew],
  );

  const {
    messages: sseMessages,
    isStreaming,
    error: sseError,
    sendMessage,
    startNewChat,
  } = useSseChat({ conversationId: effectiveConvId });

  const sidebarConversations = useMemo(
    () =>
      conversations.map((conversation, index) =>
        mapConversationToDashboard(conversation, index, locale),
      ),
    [conversations, locale],
  );

  const displayMessages = useMemo(
    () => sseMessages.map((message) => mapMessageToDashboard(message, locale)),
    [sseMessages, locale],
  );

  const openCreatedConversation = useCallback((id: string) => {
    setActiveConv(id);
    setIsComposingNew(false);
  }, []);
  const { input, setInput, handleSend } = useChatSend({
    conversationId: effectiveConvId,
    isStreaming,
    sendMessage,
    onConversationCreated: openCreatedConversation,
  });

  const handleNewChat = useCallback(() => {
    setActiveConv(null);
    setIsComposingNew(true);
    setInput("");
    startNewChat();
  }, [startNewChat, setInput]);

  const handleSelectConversation = useCallback(
    (id: string) => {
      setActiveConv(id);
      setIsComposingNew(false);
      startNewChat();
      convDrawer.close();
    },
    [startNewChat, convDrawer],
  );

  return (
    <div
      className="flex flex-col min-h-screen"
      style={{ background: DASHBOARD_CHAT_BG_DEEP }}
    >
      <ChatHeader
        onNewChat={handleNewChat}
        onToggleConversations={convDrawer.toggle}
        conversationsOpen={convDrawer.open}
        conversationsId={CHAT_CONVERSATIONS_ID}
      />
      {sseError && (
        <p className="px-6 py-2 text-sm text-red-400" role="alert">
          {sseError}
        </p>
      )}
      <div
        className="flex flex-1"
        style={{
          height: "calc(100vh - 56px)",
          minHeight: "calc(100vh - 56px)",
        }}
      >
        {convDrawer.open && (
          <button
            type="button"
            aria-label="Close conversations"
            tabIndex={-1}
            onClick={convDrawer.close}
            className="fixed inset-0 z-30 bg-black/60 md:hidden"
          />
        )}
        <ChatSidebar
          conversations={sidebarConversations}
          activeConv={effectiveConvId ?? ""}
          onSelectConversation={handleSelectConversation}
          open={convDrawer.open}
          id={CHAT_CONVERSATIONS_ID}
        />
        <div
          className="flex flex-1 flex-col"
          style={{
            background: DASHBOARD_CHAT_BG_OVERLAY_LIGHT,
          }}
        >
          <ChatMessageList
            messages={displayMessages}
            isStreaming={isStreaming}
          />
          <ChatComposer
            value={input}
            onChange={setInput}
            onSend={() => void handleSend()}
            disabled={isStreaming}
          />
        </div>
      </div>
    </div>
  );
}
