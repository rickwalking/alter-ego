import {
  DASHBOARD_CHAT_BG_HEADER,
  DASHBOARD_CHAT_BORDER_SUBTLE,
  DASHBOARD_CHAT_BORDER_LIGHT,
  DASHBOARD_CHAT_MAGENTA,
  DASHBOARD_CHAT_MONO_FONT,
  DASHBOARD_CHAT_TEXT_DIM,
  DASHBOARD_CHAT_TEXT_MUTED,
} from "@/modules/editorial-operations";

export interface ChatHeaderProps {
  onNewChat?: () => void;
}

export function ChatHeader({ onNewChat }: ChatHeaderProps): React.ReactElement {
  return (
    <header
      className="sticky top-0 z-20 shrink-0"
      style={{
        height: "56px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 32px",
        borderBottom: `1px solid ${DASHBOARD_CHAT_BORDER_SUBTLE}`,
        background: DASHBOARD_CHAT_BG_HEADER,
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <h1 style={{ fontSize: "16px", fontWeight: 700 }}>Chat</h1>
        <span
          style={{
            fontFamily: DASHBOARD_CHAT_MONO_FONT,
            fontSize: "11px",
            color: DASHBOARD_CHAT_TEXT_DIM,
          }}
        >
          / <span>Alter-Ego assistant</span>
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {onNewChat && (
          <button
            type="button"
            onClick={onNewChat}
            style={{
              padding: "6px 12px",
              borderRadius: "6px",
              border: `1px solid ${DASHBOARD_CHAT_BORDER_LIGHT}`,
              background: "transparent",
              color: DASHBOARD_CHAT_TEXT_MUTED,
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            New chat
          </button>
        )}
        <button
          type="button"
          aria-label="Notifications"
          style={{
            position: "relative",
            width: "32px",
            height: "32px",
            borderRadius: "6px",
            background: "transparent",
            border: `1px solid ${DASHBOARD_CHAT_BORDER_LIGHT}`,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
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
            aria-hidden="true"
          >
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span
            style={{
              position: "absolute",
              top: "8px",
              right: "8px",
              width: "5px",
              height: "5px",
              borderRadius: "50%",
              background: DASHBOARD_CHAT_MAGENTA,
            }}
          />
        </button>
      </div>
    </header>
  );
}
