import {
  DASHBOARD_CHAT_BG_ELEVATED,
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_CYAN_DIM,
  DASHBOARD_CHAT_MONO_FONT,
  DASHBOARD_CHAT_TEXT_MUTED,
} from "@/modules/editorial-operations";

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

/** The assistant's ◆, or a neutral person icon for whoever is chatting. */
export function ChatAvatar({
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
      data-testid="chat-user-avatar"
      style={{
        ...AVATAR_BASE_STYLE,
        background: DASHBOARD_CHAT_BG_ELEVATED,
        color: DASHBOARD_CHAT_TEXT_MUTED,
      }}
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21a8 8 0 0 1 16 0" />
      </svg>
    </div>
  );
}
