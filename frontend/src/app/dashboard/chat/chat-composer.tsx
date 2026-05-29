"use client";

import {
  DASHBOARD_CHAT_BG_DEEP,
  DASHBOARD_CHAT_BG_INPUT_BAR,
  DASHBOARD_CHAT_BG_INPUT_DARKER,
  DASHBOARD_CHAT_BORDER_MEDIUM,
  DASHBOARD_CHAT_BORDER_SUBTLE,
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_TEXT,
} from "@/features/dashboard/chat/constants";

export interface ChatComposerProps {
  value: string;
  onChange: (value: string) => void;
}

export function ChatComposer({
  value,
  onChange,
}: ChatComposerProps): React.ReactElement {
  return (
    <div
      style={{
        padding: "16px 24px",
        borderTop: `1px solid ${DASHBOARD_CHAT_BORDER_SUBTLE}`,
        background: DASHBOARD_CHAT_BG_INPUT_BAR,
      }}
    >
      <div style={{ display: "flex", gap: "10px", alignItems: "flex-end" }}>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Ask the Alter-Ego anything..."
          rows={1}
          style={{
            flex: 1,
            padding: "10px 16px",
            borderRadius: "8px",
            border: `1px solid ${DASHBOARD_CHAT_BORDER_MEDIUM}`,
            background: DASHBOARD_CHAT_BG_INPUT_DARKER,
            color: DASHBOARD_CHAT_TEXT,
            fontSize: "13px",
            fontFamily: "inherit",
            lineHeight: 1.5,
            resize: "none",
            minHeight: "42px",
            maxHeight: "120px",
            outline: "none",
          }}
        />
        <button
          type="button"
          aria-label="Send message"
          style={{
            width: "42px",
            height: "42px",
            borderRadius: "8px",
            border: "none",
            background: DASHBOARD_CHAT_CYAN,
            color: DASHBOARD_CHAT_BG_DEEP,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke={DASHBOARD_CHAT_BG_DEEP}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  );
}
