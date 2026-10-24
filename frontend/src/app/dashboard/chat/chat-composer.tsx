"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import { useTranslations } from "next-intl";
import {
  CHAT_LENGTH_COUNTER_RATIO,
  CHAT_MESSAGE_MAX_LENGTH,
} from "@/modules/conversation";
import {
  DASHBOARD_CHAT_BG_INPUT_BAR,
  DASHBOARD_CHAT_BG_INPUT_DARKER,
  DASHBOARD_CHAT_BORDER_MEDIUM,
  DASHBOARD_CHAT_BORDER_SUBTLE,
  DASHBOARD_CHAT_TEXT,
  DASHBOARD_CHAT_TEXT_DIM,
} from "@/modules/editorial-operations";
import { SendButton, StopButton } from "./chat-composer-actions";

/** The message box grows with its text up to this height, then scrolls. */
export const COMPOSER_MAX_HEIGHT_PX = 160;

interface AutoGrow {
  ref: RefObject<HTMLTextAreaElement | null>;
  /** Height and overflow for the textarea's style (React owns the style). */
  style: React.CSSProperties;
}

/** Size the textarea to its content (one line up to the max height), again on resize. */
function useAutoGrow(value: string): AutoGrow {
  const ref = useRef<HTMLTextAreaElement>(null);
  const [contentHeight, setContentHeight] = useState<number | null>(null);
  const [viewportWidth, setViewportWidth] = useState(0);
  useEffect(() => {
    const onResize = (): void => {
      setViewportWidth(window.innerWidth);
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
    };
  }, []);
  useLayoutEffect(() => {
    const textarea = ref.current;
    if (!textarea) return;
    const previous = textarea.style.height;
    textarea.style.height = "auto";
    const border = textarea.offsetHeight - textarea.clientHeight;
    const measured = textarea.scrollHeight + border;
    textarea.style.height = previous;
    setContentHeight(measured);
  }, [value, viewportWidth]);
  if (contentHeight === null) return { ref, style: {} };
  return {
    ref,
    style: {
      height: `${String(Math.min(contentHeight, COMPOSER_MAX_HEIGHT_PX))}px`,
      overflowY: contentHeight > COMPOSER_MAX_HEIGHT_PX ? "auto" : "hidden",
    },
  };
}

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
  /** A reply is streaming: Send is off, but the textarea keeps focus. */
  busy?: boolean;
  /** Stop the streaming reply; while busy, Send becomes Stop when given. */
  onStop?: () => void;
}

export function ChatComposer({
  value,
  onChange,
  onSend,
  busy = false,
  onStop,
}: Readonly<ChatComposerProps>): React.ReactElement {
  const t = useTranslations("chat.input");
  const counterId = useId();
  const { ref: textareaRef, style: growStyle } = useAutoGrow(value);
  const hadFocusRef = useRef(false);
  const noteFocusBeforeAction = (): void => {
    hadFocusRef.current = document.activeElement === textareaRef.current;
  };
  const sendAndKeepFocus = (): void => {
    onSend();
    if (hadFocusRef.current) textareaRef.current?.focus();
    hadFocusRef.current = false;
  };
  const stopAndKeepFocus = (): void => {
    onStop?.();
    if (hadFocusRef.current) textareaRef.current?.focus();
    hadFocusRef.current = false;
  };
  const showCounter = value.length >= COUNTER_FROM;
  return (
    <div
      style={{
        paddingTop: "16px",
        paddingInline: "24px",
        paddingBottom: "max(16px, env(safe-area-inset-bottom))",
        borderTop: `1px solid ${DASHBOARD_CHAT_BORDER_SUBTLE}`,
        background: DASHBOARD_CHAT_BG_INPUT_BAR,
      }}
    >
      <div className="mx-auto w-full max-w-3xl">
        <div style={{ display: "flex", gap: "10px", alignItems: "flex-end" }}>
          <textarea
            ref={textareaRef}
            aria-label={t("label")}
            className="focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon-cyan"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSend();
              }
            }}
            placeholder={t("placeholder")}
            rows={1}
            maxLength={CHAT_MESSAGE_MAX_LENGTH}
            aria-describedby={showCounter ? counterId : undefined}
            style={{
              flex: 1,
              padding: "10px 16px",
              borderRadius: "8px",
              border: `1px solid ${DASHBOARD_CHAT_BORDER_MEDIUM}`,
              background: DASHBOARD_CHAT_BG_INPUT_DARKER,
              color: DASHBOARD_CHAT_TEXT,
              fontSize: "16px",
              fontFamily: "inherit",
              lineHeight: 1.5,
              resize: "none",
              minHeight: "44px",
              maxHeight: `${String(COMPOSER_MAX_HEIGHT_PX)}px`,
              ...growStyle,
            }}
          />
          {busy && onStop ? (
            <StopButton
              label={t("stop")}
              onPointerDown={noteFocusBeforeAction}
              onClick={stopAndKeepFocus}
            />
          ) : (
            <SendButton
              label={t("send")}
              disabled={busy || !value.trim()}
              onPointerDown={noteFocusBeforeAction}
              onClick={sendAndKeepFocus}
            />
          )}
        </div>
        <LengthCounter id={counterId} count={value.length} />
      </div>
    </div>
  );
}
