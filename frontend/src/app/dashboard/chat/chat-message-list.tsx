import {
  DASHBOARD_CHAT_BG_CARD,
  DASHBOARD_CHAT_BG_ELEVATED,
  DASHBOARD_CHAT_BORDER_STRONG,
  DASHBOARD_CHAT_CARD_BORDER,
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_CYAN_DIM,
  DASHBOARD_CHAT_MONO_FONT,
  DASHBOARD_CHAT_TEXT,
  DASHBOARD_CHAT_TEXT_DIM,
  DASHBOARD_CHAT_TEXT_MUTED,
  DASHBOARD_CHAT_TYPING_LABEL,
} from "@/features/dashboard/chat/constants";
import type { DashboardChatMessage } from "@/features/dashboard/chat/types";

export interface ChatMessageListProps {
  messages: DashboardChatMessage[];
  isStreaming?: boolean;
}

export function ChatMessageList({
  messages,
  isStreaming = false,
}: ChatMessageListProps): React.ReactElement {
  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      {messages.map((msg, index) => (
        <div
          key={`${msg.role}-${index}`}
          style={{
            display: "flex",
            gap: "10px",
            maxWidth: "720px",
            flexDirection: msg.role === "user" ? "row-reverse" : "row",
            alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
          }}
        >
          {msg.role === "assistant" ? (
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: DASHBOARD_CHAT_MONO_FONT,
                fontSize: "14px",
                fontWeight: 700,
                flexShrink: 0,
                background: DASHBOARD_CHAT_CYAN_DIM,
                color: DASHBOARD_CHAT_CYAN,
              }}
            >
              ◆
            </div>
          ) : (
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: DASHBOARD_CHAT_MONO_FONT,
                fontSize: "11px",
                fontWeight: 700,
                flexShrink: 0,
                background: DASHBOARD_CHAT_BG_ELEVATED,
                color: DASHBOARD_CHAT_TEXT_MUTED,
              }}
            >
              PM
            </div>
          )}
          <div>
            <div
              style={{
                padding: "10px 16px",
                borderRadius: "10px",
                fontSize: "13px",
                lineHeight: 1.65,
                whiteSpace: "pre-wrap",
                background:
                  msg.role === "assistant"
                    ? DASHBOARD_CHAT_BG_CARD
                    : DASHBOARD_CHAT_CYAN_DIM,
                border:
                  msg.role === "assistant"
                    ? `1px solid ${DASHBOARD_CHAT_CARD_BORDER}`
                    : `1px solid ${DASHBOARD_CHAT_BORDER_STRONG}`,
                color:
                  msg.role === "assistant"
                    ? DASHBOARD_CHAT_TEXT_MUTED
                    : DASHBOARD_CHAT_TEXT,
              }}
            >
              {msg.text}
            </div>
            <div
              style={{
                fontFamily: DASHBOARD_CHAT_MONO_FONT,
                fontSize: "9px",
                color: DASHBOARD_CHAT_TEXT_DIM,
                marginTop: "4px",
                textAlign: msg.role === "user" ? "right" : "left",
              }}
            >
              {msg.time}
            </div>
          </div>
        </div>
      ))}
      {isStreaming && (
        <div
          style={{
            display: "flex",
            gap: "10px",
            maxWidth: "720px",
            opacity: 0.6,
          }}
        >
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: DASHBOARD_CHAT_MONO_FONT,
              fontSize: "14px",
              fontWeight: 700,
              flexShrink: 0,
              background: DASHBOARD_CHAT_CYAN_DIM,
              color: DASHBOARD_CHAT_CYAN,
            }}
          >
            ◆
          </div>
          <div
            style={{
              padding: "10px 16px",
              borderRadius: "10px",
              fontSize: "13px",
              background: DASHBOARD_CHAT_BG_CARD,
              border: `1px solid ${DASHBOARD_CHAT_CARD_BORDER}`,
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <span
              style={{
                display: "inline-block",
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: DASHBOARD_CHAT_CYAN,
              }}
            />
            {DASHBOARD_CHAT_TYPING_LABEL}
          </div>
        </div>
      )}
    </div>
  );
}
