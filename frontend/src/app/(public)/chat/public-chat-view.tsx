"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { useCreateConversation } from "@/modules/conversation";
import { useSseChat } from "@/modules/conversation";
import {
  AGENT_ORIGIN_ALTER_EGO,
  CONVERSATION_METADATA_AGENT_ORIGIN,
} from "@/constants/publish-chat";
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

export function PublicChatView(): React.ReactElement {
  const [activeConv, setActiveConv] = useState<string | null>(null);
  const [input, setInput] = useState("");

  const createConversation = useCreateConversation();

  const {
    messages: sseMessages,
    isStreaming,
    error: sseError,
    sendMessage,
    startNewChat,
  } = useSseChat({
    conversationId: activeConv,
    enableHistory: false,
  });

  const displayMessages = useMemo(
    () => sseMessages.map(mapMessageToDashboard),
    [sseMessages],
  );

  const handleSend = useCallback(async () => {
    const content = input.trim();
    if (!content || isStreaming) return;

    let convId = activeConv;
    if (!convId) {
      const created = await createConversation.mutateAsync({
        metadata: {
          [CONVERSATION_METADATA_AGENT_ORIGIN]: AGENT_ORIGIN_ALTER_EGO,
        },
      });
      convId = created.id;
      setActiveConv(convId);
    }

    setInput("");
    await sendMessage(content, convId);
  }, [input, isStreaming, activeConv, createConversation, sendMessage]);

  const handleNewChat = useCallback(() => {
    setActiveConv(null);
    setInput("");
    startNewChat();
  }, [startNewChat]);

  return (
    <div
      className="flex h-full min-h-0 flex-col"
      style={{ background: DASHBOARD_CHAT_BG_DEEP }}
    >
      <ChatHeader onNewChat={handleNewChat} />
      {sseError && (
        <p className="shrink-0 px-6 py-2 text-sm text-red-400" role="alert">
          {sseError}
        </p>
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
