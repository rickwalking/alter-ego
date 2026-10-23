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
} from "@/modules/editorial-operations";
import { ChatMarkdown } from "./chat-markdown";
import type { DashboardChatMessage } from "@/modules/editorial-operations";

const AVATAR_BASE_STYLE: React.CSSProperties = {
  width: "32px",
  height: "32px",
  borderRadius: "50%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontFamily: DASHBOARD_CHAT_MONO_FONT,
  fontWeight: 700,
  flexShrink: 0,
};

/** The assistant's ◆ or the owner's initials. */
function ChatAvatar({
  assistant,
}: Readonly<{ assistant: boolean }>): React.ReactElement {
  if (assistant) {
    return (
      <div
        style={{
          ...AVATAR_BASE_STYLE,
          fontSize: "14px",
          background: DASHBOARD_CHAT_CYAN_DIM,
          color: DASHBOARD_CHAT_CYAN,
        }}
      >
        ◆
      </div>
    );
  }
  return (
    <div
      style={{
        ...AVATAR_BASE_STYLE,
        fontSize: "11px",
        background: DASHBOARD_CHAT_BG_ELEVATED,
        color: DASHBOARD_CHAT_TEXT_MUTED,
      }}
    >
      PM
    </div>
  );
}

/** One message: avatar, bubble and time, mirrored for the owner. */
export function ChatMessageRow({
  msg,
}: Readonly<{
  msg: DashboardChatMessage;
}>): React.ReactElement {
  const assistant = msg.role === "assistant";
  const user = msg.role === "user";
  return (
    <div
      style={{
        display: "flex",
        gap: "10px",
        maxWidth: "min(720px, 100%)",
        flexDirection: user ? "row-reverse" : "row",
        alignSelf: user ? "flex-end" : "flex-start",
      }}
    >
      <ChatAvatar assistant={assistant} />
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            padding: "10px 16px",
            borderRadius: "10px",
            fontSize: "13px",
            lineHeight: 1.65,
            whiteSpace: assistant ? "normal" : "pre-wrap",
            overflowWrap: "anywhere",
            background: assistant
              ? DASHBOARD_CHAT_BG_CARD
              : DASHBOARD_CHAT_CYAN_DIM,
            border: assistant
              ? `1px solid ${DASHBOARD_CHAT_CARD_BORDER}`
              : `1px solid ${DASHBOARD_CHAT_BORDER_STRONG}`,
            color: assistant ? DASHBOARD_CHAT_TEXT_MUTED : DASHBOARD_CHAT_TEXT,
          }}
        >
          {assistant ? <ChatMarkdown text={msg.text} /> : msg.text}
        </div>
        <div
          style={{
            fontFamily: DASHBOARD_CHAT_MONO_FONT,
            fontSize: "9px",
            color: DASHBOARD_CHAT_TEXT_DIM,
            marginTop: "4px",
            textAlign: user ? "right" : "left",
          }}
        >
          {msg.time}
        </div>
      </div>
    </div>
  );
}

/** The assistant's "typing" bubble while a reply streams. */
export function TypingIndicator({
  label,
}: Readonly<{ label: string }>): React.ReactElement {
  return (
    <div
      style={{ display: "flex", gap: "10px", maxWidth: "720px", opacity: 0.6 }}
    >
      <ChatAvatar assistant />
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
          className="chat-typing-dot"
          style={{
            display: "inline-block",
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            background: DASHBOARD_CHAT_CYAN,
          }}
        />
        {label}
      </div>
    </div>
  );
}
