"use client";

import { useRef } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { useFocusTrap } from "@/lib/use-focus-trap";
import { useScrollLock } from "@/lib/use-scroll-lock";
import { useMediaQuery } from "@/lib/use-media-query";
import { CHAT_DRAWER_MEDIA_QUERY } from "./use-menu-button-hidden";
import {
  DASHBOARD_CHAT_BORDER_SUBTLE,
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
  /** The search box text; the conversations passed in already match it. */
  query?: string;
  onQueryChange?: (query: string) => void;
  /** The server is still looking for older matches. */
  searching?: boolean;
  /** More conversations can be loaded. */
  hasMore?: boolean;
  onLoadMore?: () => void;
}

export { filterConversations } from "./chat-sidebar-filter";
import {
  ChatSidebarMore,
  ChatSidebarNoMatches,
  ChatSidebarSearch,
} from "./chat-sidebar-parts";

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
  query = "",
  onQueryChange,
  searching = false,
  hasMore = false,
  onLoadMore,
}: Readonly<ChatSidebarProps>): React.ReactElement {
  const t = useTranslations("chat.sidebar");
  const ref = useRef<HTMLDivElement>(null);
  const isOpen = open === true;
  const isDrawer = useMediaQuery(CHAT_DRAWER_MEDIA_QUERY);
  const drawerActive = isOpen && isDrawer;

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
      <ChatSidebarSearch
        query={query}
        onQueryChange={onQueryChange}
        label={t("searchLabel")}
        placeholder={t("searchPlaceholder")}
      />
      <div style={{ flex: 1, overflowY: "auto", padding: "8px" }}>
        <ChatSidebarNoMatches
          show={conversations.length === 0 && query.trim() !== "" && !searching}
          label={t("noMatches")}
        />
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
        <ChatSidebarMore
          onLoadMore={hasMore ? onLoadMore : undefined}
          label={t("showMore")}
        />
      </div>
    </div>
  );
}
