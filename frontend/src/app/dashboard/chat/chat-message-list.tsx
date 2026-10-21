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
} from "@/modules/editorial-operations";
import type { DashboardChatMessage } from "@/modules/editorial-operations";

export interface ChatMessageListProps {
  messages: DashboardChatMessage[];
  isStreaming?: boolean;
}

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
function ChatAvatar({ assistant }: { assistant: boolean }): React.ReactElement {
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
function ChatMessageRow({
  msg,
}: {
  msg: DashboardChatMessage;
}): React.ReactElement {
  const assistant = msg.role === "assistant";
  const user = msg.role === "user";
  return (
    <div
      style={{
        display: "flex",
        gap: "10px",
        maxWidth: "720px",
        flexDirection: user ? "row-reverse" : "row",
        alignSelf: user ? "flex-end" : "flex-start",
      }}
    >
      <ChatAvatar assistant={assistant} />
      <div>
        <div
          style={{
            padding: "10px 16px",
            borderRadius: "10px",
            fontSize: "13px",
            lineHeight: 1.65,
            whiteSpace: "pre-wrap",
            background: assistant
              ? DASHBOARD_CHAT_BG_CARD
              : DASHBOARD_CHAT_CYAN_DIM,
            border: assistant
              ? `1px solid ${DASHBOARD_CHAT_CARD_BORDER}`
              : `1px solid ${DASHBOARD_CHAT_BORDER_STRONG}`,
            color: assistant ? DASHBOARD_CHAT_TEXT_MUTED : DASHBOARD_CHAT_TEXT,
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
function TypingIndicator(): React.ReactElement {
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
        {DASHBOARD_CHAT_TYPING_LABEL}
      </div>
    </div>
  );
}

export function ChatMessageList({
  messages,
  isStreaming = false,
}: Readonly<ChatMessageListProps>): React.ReactElement {
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
        <ChatMessageRow key={`${msg.role}-${index}`} msg={msg} />
      ))}
      {isStreaming && <TypingIndicator />}
      <style>{`
        @keyframes chat-pulse-dot {
          0%, 100% { opacity: 0.35; transform: scale(0.85); }
          50% { opacity: 1; transform: scale(1.15); }
        }
        .chat-typing-dot {
          animation: chat-pulse-dot 1.2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
