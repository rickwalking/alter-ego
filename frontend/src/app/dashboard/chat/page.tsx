"use client";

import { useState } from "react";
import { DASHBOARD_CHAT_BG_DEEP, DASHBOARD_CHAT_BG_OVERLAY_LIGHT } from "@/features/dashboard/chat/constants";
import {
  MOCK_DASHBOARD_CONVERSATIONS,
  MOCK_DASHBOARD_MESSAGES,
} from "@/features/dashboard/chat/mock-data";
import { ChatComposer } from "@/app/dashboard/chat/chat-composer";
import { ChatHeader } from "@/app/dashboard/chat/chat-header";
import { ChatMessageList } from "@/app/dashboard/chat/chat-message-list";
import { ChatSidebar } from "@/app/dashboard/chat/chat-sidebar";

export default function ChatPage(): React.ReactElement {
  const [activeConv, setActiveConv] = useState("1");
  const [input, setInput] = useState("");

  return (
    <div
      className="flex flex-col min-h-screen"
      style={{ background: DASHBOARD_CHAT_BG_DEEP }}
    >
      <ChatHeader />
      <div
        className="flex flex-1"
        style={{
          height: "calc(100vh - 56px - 240px)",
          minHeight: "calc(100vh - 56px)",
        }}
      >
        <ChatSidebar
          conversations={MOCK_DASHBOARD_CONVERSATIONS}
          activeConv={activeConv}
          onSelectConversation={setActiveConv}
        />
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            background: DASHBOARD_CHAT_BG_OVERLAY_LIGHT,
          }}
        >
          <ChatMessageList messages={MOCK_DASHBOARD_MESSAGES} />
          <ChatComposer value={input} onChange={setInput} />
        </div>
      </div>
    </div>
  );
}
