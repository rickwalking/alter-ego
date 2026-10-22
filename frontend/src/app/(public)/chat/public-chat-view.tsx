"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { useLocale } from "next-intl";
import { useSseChat } from "@/modules/conversation";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { mapMessageToDashboard } from "@/modules/editorial-operations";
import {
  DASHBOARD_CHAT_BG_DEEP,
  DASHBOARD_CHAT_BG_OVERLAY_LIGHT,
  DASHBOARD_CHAT_TEXT_MUTED,
} from "@/modules/editorial-operations";
import { ChatComposer } from "@/app/dashboard/chat/chat-composer";
import { ChatHeader } from "@/app/dashboard/chat/chat-header";
import { ChatMessageList } from "@/app/dashboard/chat/chat-message-list";
import { useChatSend } from "@/app/dashboard/chat/use-chat-send";
import { ChatErrorBanner } from "@/app/dashboard/chat/chat-error-banner";

export function PublicChatView(): React.ReactElement {
  const [activeConv, setActiveConv] = useState<string | null>(null);
  const locale = useLocale();

  const {
    messages: sseMessages,
    isStreaming,
    error: sseError,
    sendMessage,
    isBusy,
    startNewChat,
  } = useSseChat({
    conversationId: activeConv,
    enableHistory: false,
  });

  const { input, setInput, handleSend, retry } = useChatSend({
    conversationId: activeConv,
    isStreaming,
    sendMessage,
    isBusy,
    onConversationCreated: setActiveConv,
  });

  const displayMessages = useMemo(
    () => sseMessages.map((message) => mapMessageToDashboard(message, locale)),
    [sseMessages, locale],
  );

  const handleNewChat = useCallback(() => {
    setActiveConv(null);
    setInput("");
    startNewChat();
  }, [startNewChat, setInput]);

  return (
    <div
      className="flex h-full min-h-0 flex-col"
      style={{ background: DASHBOARD_CHAT_BG_DEEP }}
    >
      <ChatHeader onNewChat={handleNewChat} />
      {sseError && (
        <ChatErrorBanner
          kind={sseError}
          onRetry={() => void retry()}
          onNewChat={handleNewChat}
        />
      )}
      <div
        className="flex min-h-0 flex-1 flex-col"
        style={{ background: DASHBOARD_CHAT_BG_OVERLAY_LIGHT }}
      >
        <p
          className="shrink-0 px-6 py-2 text-xs"
          style={{ color: DASHBOARD_CHAT_TEXT_MUTED }}
        >
          Messages are not saved after refresh.{" "}
          <Link
            href={PUBLIC_ROUTE_PATHS.LOGIN}
            style={{ color: "inherit", textDecoration: "underline" }}
          >
            Sign in
          </Link>{" "}
          to keep chat history.
        </p>
        <ChatMessageList messages={displayMessages} isStreaming={isStreaming} />
        <ChatComposer
          value={input}
          onChange={setInput}
          onSend={() => void handleSend()}
          disabled={isStreaming}
        />
      </div>
    </div>
  );
}
