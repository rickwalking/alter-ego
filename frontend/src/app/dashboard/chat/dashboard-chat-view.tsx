"use client";

import { useCallback, useMemo, useState } from "react";
import { useRecheckSessionOnNotFound } from "@/app/dashboard/chat/use-recheck-session";
import { useLocale, useTranslations } from "next-intl";
import { useSseChat } from "@/modules/conversation";
import { mapMessageToDashboard } from "@/modules/editorial-operations";
import {
  DASHBOARD_CHAT_BG_DEEP,
  DASHBOARD_CHAT_BG_OVERLAY_LIGHT,
} from "@/modules/editorial-operations";
import { ChatComposer } from "@/app/dashboard/chat/chat-composer";
import { ChatHeader } from "@/app/dashboard/chat/chat-header";
import { ChatMessageList } from "@/app/dashboard/chat/chat-message-list";
import { ChatSidebar } from "@/app/dashboard/chat/chat-sidebar";
import { useChatSend } from "@/app/dashboard/chat/use-chat-send";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { ChatErrorBanner } from "@/app/dashboard/chat/chat-error-banner";
import { useOffCanvas } from "@/lib/use-off-canvas";
import { useMenuButtonHidden } from "@/app/dashboard/chat/use-menu-button-hidden";
import { useSidebarConversations } from "@/app/dashboard/chat/use-sidebar-conversations";

const CHAT_CONVERSATIONS_ID = "chat-conversations";

export function DashboardChatView(): React.ReactElement {
  const [activeConv, setActiveConv] = useState<string | null>(null);
  const locale = useLocale();
  const t = useTranslations("chat");
  const untitled = t("sidebar.untitled");
  const [isComposingNew, setIsComposingNew] = useState(false);
  const convDrawer = useOffCanvas();
  useMenuButtonHidden(convDrawer.open);

  const {
    loaded: conversations,
    refetch: refetchConversations,
    sidebar,
  } = useSidebarConversations(locale, untitled);

  const effectiveConvId = useMemo(
    () =>
      isComposingNew ? null : (activeConv ?? conversations[0]?.id ?? null),
    [activeConv, conversations, isComposingNew],
  );

  const {
    messages: sseMessages,
    isStreaming,
    awaitingReply,
    error: sseError,
    canRetry,
    sendMessage,
    isBusy,
    startNewChat,
    stopStreaming,
  } = useSseChat({ conversationId: effectiveConvId });
  useRecheckSessionOnNotFound(sseError, refetchConversations);

  const displayMessages = useMemo(
    () => sseMessages.map((message) => mapMessageToDashboard(message, locale)),
    [sseMessages, locale],
  );

  const openCreatedConversation = useCallback((id: string) => {
    setActiveConv(id);
    setIsComposingNew(false);
  }, []);
  const replyPending = isStreaming || awaitingReply;
  const { input, setInput, handleSend, retry, forgetFailed, sendNow } =
    useChatSend({
      conversationId: effectiveConvId,
      isStreaming: replyPending,
      sendMessage,
      isBusy,
      onConversationCreated: openCreatedConversation,
    });

  const handleNewChat = useCallback(() => {
    setActiveConv(null);
    setIsComposingNew(true);
    setInput("");
    forgetFailed();
    startNewChat();
  }, [startNewChat, setInput, forgetFailed]);

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
        <ChatErrorBanner
          kind={sseError}
          loginRedirect={DASHBOARD_ROUTES.CHAT}
          canRetry={canRetry}
          onRetry={() => void retry()}
          onNewChat={handleNewChat}
        />
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
            aria-label={t("closeConversations")}
            tabIndex={-1}
            onClick={convDrawer.close}
            className="fixed inset-0 z-30 bg-black/60 md:hidden"
          />
        )}
        <ChatSidebar
          {...sidebar}
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
            isStreaming={replyPending}
            onSuggestion={
              effectiveConvId ? undefined : (text) => void sendNow(text)
            }
          />
          <ChatComposer
            value={input}
            onChange={setInput}
            onSend={() => void handleSend()}
            busy={replyPending}
            onStop={isStreaming ? stopStreaming : undefined}
          />
        </div>
      </div>
    </div>
  );
}
