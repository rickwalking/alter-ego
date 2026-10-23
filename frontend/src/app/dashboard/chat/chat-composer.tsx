"use client";

import { useId } from "react";
import { useTranslations } from "next-intl";
import {
  CHAT_LENGTH_COUNTER_RATIO,
  CHAT_MESSAGE_MAX_LENGTH,
} from "@/modules/conversation";
import {
  DASHBOARD_CHAT_BG_DEEP,
  DASHBOARD_CHAT_BG_INPUT_BAR,
  DASHBOARD_CHAT_BG_INPUT_DARKER,
  DASHBOARD_CHAT_BORDER_MEDIUM,
  DASHBOARD_CHAT_BORDER_SUBTLE,
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_TEXT,
  DASHBOARD_CHAT_TEXT_DIM,
} from "@/modules/editorial-operations";

const COUNTER_FROM = Math.floor(
  CHAT_MESSAGE_MAX_LENGTH * CHAT_LENGTH_COUNTER_RATIO,
);

/** "n of 2000 characters", shown once the text nears the limit. */
function LengthCounter({
  id,
  count,
}: Readonly<{ id: string; count: number }>): React.ReactElement | null {
  const t = useTranslations("chat.input");
  if (count < COUNTER_FROM) return null;
  return (
    <p
      id={id}
      style={{
        margin: "6px 0 0",
        fontSize: "12px",
        textAlign: "right",
        color: DASHBOARD_CHAT_TEXT_DIM,
      }}
    >
      {t("counter", { count, max: CHAT_MESSAGE_MAX_LENGTH })}
    </p>
  );
}

export interface ChatComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
}

export function ChatComposer({
  value,
  onChange,
  onSend,
  disabled = false,
}: Readonly<ChatComposerProps>): React.ReactElement {
  const counterId = useId();
  const showCounter = value.length >= COUNTER_FROM;
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
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          placeholder="Ask the Alter-Ego anything..."
          rows={1}
          maxLength={CHAT_MESSAGE_MAX_LENGTH}
          aria-describedby={showCounter ? counterId : undefined}
          disabled={disabled}
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
          onClick={onSend}
          disabled={disabled || !value.trim()}
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
      <LengthCounter id={counterId} count={value.length} />
    </div>
  );
}
