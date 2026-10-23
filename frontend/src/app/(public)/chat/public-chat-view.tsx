"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { MAIN_CONTENT_ID } from "@/constants/a11y";
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
  const t = useTranslations("chat");

  const {
    messages: sseMessages,
    isStreaming,
    error: sseError,
    canRetry,
    sendMessage,
    isBusy,
    startNewChat,
  } = useSseChat({
    conversationId: activeConv,
    enableHistory: false,
  });

  const { input, setInput, handleSend, retry, forgetFailed } = useChatSend({
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
    forgetFailed();
    startNewChat();
  }, [startNewChat, setInput, forgetFailed]);

  return (
    <div
      className="flex h-full min-h-0 flex-col"
      style={{ background: DASHBOARD_CHAT_BG_DEEP }}
    >
      <ChatHeader onNewChat={handleNewChat} />
      {sseError && (
        <ChatErrorBanner
          kind={sseError}
          canRetry={canRetry}
          onRetry={() => void retry()}
          onNewChat={handleNewChat}
        />
      )}
      <main
        id={MAIN_CONTENT_ID}
        tabIndex={-1}
        className="flex min-h-0 flex-1 flex-col"
        style={{ background: DASHBOARD_CHAT_BG_OVERLAY_LIGHT }}
      >
        <p
          className="shrink-0 px-6 py-2 text-xs"
          style={{ color: DASHBOARD_CHAT_TEXT_MUTED }}
        >
          {t("hintNotSaved")}{" "}
          <Link
            href={PUBLIC_ROUTE_PATHS.LOGIN}
            style={{ color: "inherit", textDecoration: "underline" }}
          >
            {t("hintSignIn")}
          </Link>
        </p>
        <ChatMessageList messages={displayMessages} isStreaming={isStreaming} />
        <ChatComposer
          value={input}
          onChange={setInput}
          onSend={() => void handleSend()}
          busy={isStreaming}
        />
      </main>
    </div>
  );
}
