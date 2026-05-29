"use client";

import { useCallback, useMemo, useState } from "react";
import {
  useConversations,
  useCreateConversation,
} from "@/features/chat/hooks/use-chat";
import { useSseChat } from "@/features/chat/hooks/use-sse-chat";
import {
  AGENT_ORIGIN_ALTER_EGO,
  CONVERSATION_METADATA_AGENT_ORIGIN,
} from "@/constants/publish-chat";
import {
  mapConversationToDashboard,
  mapMessageToDashboard,
} from "@/features/dashboard/chat/adapters/chat-adapter";
import {
  DASHBOARD_CHAT_BG_DEEP,
  DASHBOARD_CHAT_BG_OVERLAY_LIGHT,
} from "@/features/dashboard/chat/constants";
import { ChatComposer } from "@/app/dashboard/chat/chat-composer";
import { ChatHeader } from "@/app/dashboard/chat/chat-header";
import { ChatMessageList } from "@/app/dashboard/chat/chat-message-list";
import { ChatSidebar } from "@/app/dashboard/chat/chat-sidebar";

export default function ChatPage(): React.ReactElement {
  const [activeConv, setActiveConv] = useState<string | null>(null);
  const [isComposingNew, setIsComposingNew] = useState(false);
  const [input, setInput] = useState("");

  const { data: conversations = [] } = useConversations();
  const createConversation = useCreateConversation();

  const effectiveConvId = useMemo(
    () =>
      isComposingNew
        ? null
        : (activeConv ??
          (conversations.length > 0 ? conversations[0].id : null)),
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
    () => conversations.map(mapConversationToDashboard),
    [conversations],
  );

  const displayMessages = useMemo(
    () => sseMessages.map(mapMessageToDashboard),
    [sseMessages],
  );

  const handleSend = useCallback(async () => {
    const content = input.trim();
    if (!content || isStreaming) return;

    let convId = effectiveConvId;
    if (!convId) {
      const created = await createConversation.mutateAsync({
        metadata: {
          [CONVERSATION_METADATA_AGENT_ORIGIN]: AGENT_ORIGIN_ALTER_EGO,
        },
      });
      convId = created.id;
      setActiveConv(convId);
      setIsComposingNew(false);
    }

    setInput("");
    await sendMessage(content, convId);
  }, [
    input,
    isStreaming,
    effectiveConvId,
    createConversation,
    sendMessage,
  ]);

  const handleNewChat = useCallback(() => {
    setActiveConv(null);
    setIsComposingNew(true);
    setInput("");
    startNewChat();
  }, [startNewChat]);

  const handleSelectConversation = useCallback(
    (id: string) => {
      setActiveConv(id);
      setIsComposingNew(false);
      startNewChat();
    },
    [startNewChat],
  );

  return (
    <div
      className="flex flex-col min-h-screen"
      style={{ background: DASHBOARD_CHAT_BG_DEEP }}
    >
      <ChatHeader onNewChat={handleNewChat} />
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
        <ChatSidebar
          conversations={sidebarConversations}
          activeConv={effectiveConvId ?? ""}
          onSelectConversation={handleSelectConversation}
        />
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
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
