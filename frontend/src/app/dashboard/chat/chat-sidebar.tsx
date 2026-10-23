"use client";

import { useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { useFocusTrap } from "@/lib/use-focus-trap";
import { useScrollLock } from "@/lib/use-scroll-lock";
import { useMediaQuery } from "@/lib/use-media-query";
import { CHAT_DRAWER_MEDIA_QUERY } from "./use-menu-button-hidden";
import {
  DASHBOARD_CHAT_BORDER_LIGHT,
  DASHBOARD_CHAT_BORDER_SUBTLE,
  DASHBOARD_CHAT_BG_INPUT_DARK,
  DASHBOARD_CHAT_BG_DEEP,
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

/** Case- and accent-insensitive form used to match a search query. */
function searchable(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase();
}

/** The conversations whose title contains the query (all when it is blank). */
export function filterConversations(
  conversations: DashboardConversation[],
  query: string,
): DashboardConversation[] {
  const needle = searchable(query.trim());
  if (!needle) return conversations;
  return conversations.filter((conv) => searchable(conv.name).includes(needle));
}

/**
 * Below md the list is an off-canvas drawer; at md+ it is a persistent 280px
 * pane, so the focus trap and scroll lock never engage there even if `open` is
 * stale from mobile. Reuses the shared useFocusTrap/useScrollLock primitives
 * rather than duplicating drawer logic (jscpd gate).
 */
export function ChatSidebar({
  conversations,
  activeConv,
  onSelectConversation,
  open,
  id,
}: Readonly<ChatSidebarProps>): React.ReactElement {
  const t = useTranslations("chat.sidebar");
  const ref = useRef<HTMLDivElement>(null);
  const isOpen = open === true;
  const isDrawer = useMediaQuery(CHAT_DRAWER_MEDIA_QUERY);
  const drawerActive = isOpen && isDrawer;
  const [query, setQuery] = useState("");
  const visible = useMemo(
    () => filterConversations(conversations, query),
    [conversations, query],
  );

  useFocusTrap(ref, drawerActive);
  useScrollLock(drawerActive);

  return (
    <div
      ref={ref}
      id={id}
      className={cn(
        "fixed inset-y-0 left-0 z-40 flex w-[280px] shrink-0 flex-col",
        "transition-transform duration-200 ease-out",
        "md:static md:z-auto md:translate-x-0",
        isOpen ? "translate-x-0" : "-translate-x-full",
      )}
      style={{
        borderRight: `1px solid ${DASHBOARD_CHAT_BORDER_SUBTLE}`,
        background: DASHBOARD_CHAT_BG_DEEP,
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
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label={t("searchLabel")}
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
        {visible.length === 0 && query.trim() !== "" && (
          <p
            style={{
              padding: "10px 12px",
              fontSize: "12px",
              color: DASHBOARD_CHAT_TEXT_DIM,
            }}
          >
            {t("noMatches")}
          </p>
        )}
        {visible.map((conv) => (
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
          </div>
        ))}
      </div>
    </div>
  );
}
