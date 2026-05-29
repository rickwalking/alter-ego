"use client";

import {
  DASHBOARD_CHAT_BORDER_LIGHT,
  DASHBOARD_CHAT_BORDER_SUBTLE,
  DASHBOARD_CHAT_BG_INPUT_DARK,
  DASHBOARD_CHAT_BG_OVERLAY,
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_CYAN_DIM,
  DASHBOARD_CHAT_MONO_FONT,
  DASHBOARD_CHAT_TEXT,
  DASHBOARD_CHAT_TEXT_DIM,
} from "@/features/dashboard/chat/constants";
import type { DashboardConversation } from "@/features/dashboard/chat/types";

export interface ChatSidebarProps {
  conversations: DashboardConversation[];
  activeConv: string;
  onSelectConversation: (id: string) => void;
}

export function ChatSidebar({
  conversations,
  activeConv,
  onSelectConversation,
}: ChatSidebarProps): React.ReactElement {
  return (
    <div
      style={{
        width: "280px",
        flexShrink: 0,
        borderRight: `1px solid ${DASHBOARD_CHAT_BORDER_SUBTLE}`,
        display: "flex",
        flexDirection: "column",
        background: DASHBOARD_CHAT_BG_OVERLAY,
      }}
    >
      <div
        style={{
          padding: "16px",
          borderBottom: `1px solid ${DASHBOARD_CHAT_BORDER_SUBTLE}`,
        }}
      >
        <input
          type="search"
          placeholder="Search conversations..."
          style={{
            width: "100%",
            padding: "8px 12px",
            borderRadius: "6px",
            border: `1px solid ${DASHBOARD_CHAT_BORDER_LIGHT}`,
            background: DASHBOARD_CHAT_BG_INPUT_DARK,
            color: DASHBOARD_CHAT_TEXT,
            fontSize: "13px",
            fontFamily: "inherit",
            outline: "none",
          }}
        />
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "8px" }}>
        {conversations.map((conv) => (
          <div
            key={conv.id}
            role="button"
            tabIndex={0}
            onClick={() => onSelectConversation(conv.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                onSelectConversation(conv.id);
              }
            }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "10px 12px",
              borderRadius: "6px",
              cursor: "pointer",
              background:
                activeConv === conv.id ? DASHBOARD_CHAT_CYAN_DIM : "transparent",
              transition: "background 0.2s",
            }}
          >
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: DASHBOARD_CHAT_MONO_FONT,
                fontSize: "12px",
                fontWeight: 700,
                flexShrink: 0,
                background: conv.bg,
                color: conv.color,
              }}
            >
              {conv.avatar}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: "13px",
                  fontWeight: 600,
                  color: DASHBOARD_CHAT_TEXT,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {conv.name}
              </div>
              <div
                style={{
                  fontSize: "12px",
                  color: DASHBOARD_CHAT_TEXT_DIM,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  marginTop: "2px",
                }}
              >
                {conv.preview}
              </div>
            </div>
            <div
              style={{
                fontFamily: DASHBOARD_CHAT_MONO_FONT,
                fontSize: "10px",
                color: DASHBOARD_CHAT_TEXT_DIM,
                flexShrink: 0,
              }}
            >
              {conv.time}
            </div>
            {conv.unread && (
              <div
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  background: DASHBOARD_CHAT_CYAN,
                  flexShrink: 0,
                }}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
