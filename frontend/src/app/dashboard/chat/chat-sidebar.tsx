"use client";

import { useRef } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { useFocusTrap } from "@/lib/use-focus-trap";
import { useScrollLock } from "@/lib/use-scroll-lock";
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
} from "@/modules/editorial-operations";
import type { DashboardConversation } from "@/modules/editorial-operations";

export interface ChatSidebarProps {
  conversations: DashboardConversation[];
  activeConv: string;
  onSelectConversation: (id: string) => void;
  /** Drawer open state (mobile off-canvas). Omit for an always-static pane. */
  open?: boolean;
  /** DOM id so the chat header toggle can wire `aria-controls`. */
  id?: string;
}

export function ChatSidebar({
  conversations,
  activeConv,
  onSelectConversation,
  open,
  id,
}: ChatSidebarProps): React.ReactElement {
  const t = useTranslations("chat.sidebar");
  const ref = useRef<HTMLDivElement>(null);
  const isOpen = open === true;

  // Reuse the AE-0273 primitives — no duplicated drawer logic (jscpd gate).
  useFocusTrap(ref, isOpen);
  useScrollLock(isOpen);

  return (
    <div
      ref={ref}
      id={id}
      // Off-canvas drawer below md, persistent 280px pane at md+.
      className={cn(
        "fixed inset-y-0 left-0 z-40 flex w-[280px] shrink-0 flex-col",
        "transition-transform duration-200 ease-out",
        "md:static md:z-auto md:translate-x-0",
        isOpen ? "translate-x-0" : "-translate-x-full",
      )}
      style={{
        borderRight: `1px solid ${DASHBOARD_CHAT_BORDER_SUBTLE}`,
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
          placeholder={t("searchPlaceholder")}
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
                activeConv === conv.id
                  ? DASHBOARD_CHAT_CYAN_DIM
                  : "transparent",
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
