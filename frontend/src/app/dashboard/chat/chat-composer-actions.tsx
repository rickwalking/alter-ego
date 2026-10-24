"use client";

import {
  DASHBOARD_CHAT_BG_DEEP,
  DASHBOARD_CHAT_BORDER_STRONG,
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_TEXT,
} from "@/modules/editorial-operations";

const ACTION_CLASS =
  "flex h-11 w-11 shrink-0 items-center justify-center rounded-lg transition-[opacity,filter,transform] duration-150 ease-out motion-reduce:transition-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon-cyan";

/** The cyan Send button; dimmed and inert while there is nothing to send. */
export function SendButton({
  label,
  disabled,
  onClick,
  onPointerDown,
}: Readonly<{
  label: string;
  disabled: boolean;
  onClick: () => void;
  onPointerDown?: () => void;
}>): React.ReactElement {
  return (
    <button
      type="button"
      aria-label={label}
      onPointerDown={onPointerDown}
      onClick={onClick}
      disabled={disabled}
      className={`${ACTION_CLASS} enabled:hover:brightness-110 enabled:active:scale-95 disabled:cursor-not-allowed disabled:opacity-40`}
      style={{
        border: "none",
        background: DASHBOARD_CHAT_CYAN,
        color: DASHBOARD_CHAT_BG_DEEP,
      }}
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <line x1="22" y1="2" x2="11" y2="13" />
        <polygon points="22 2 15 22 11 13 2 9 22 2" />
      </svg>
    </button>
  );
}

/** Replaces Send while a reply streams: stops it, keeping what arrived. */
export function StopButton({
  label,
  onClick,
  onPointerDown,
}: Readonly<{
  label: string;
  onClick: () => void;
  onPointerDown?: () => void;
}>): React.ReactElement {
  return (
    <button
      type="button"
      aria-label={label}
      onPointerDown={onPointerDown}
      onClick={onClick}
      className={`${ACTION_CLASS} hover:brightness-125 active:scale-95`}
      style={{
        border: `1px solid ${DASHBOARD_CHAT_BORDER_STRONG}`,
        background: DASHBOARD_CHAT_BG_DEEP,
        color: DASHBOARD_CHAT_TEXT,
      }}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
        <rect x="5" y="5" width="14" height="14" rx="2" fill="currentColor" />
      </svg>
    </button>
  );
}
