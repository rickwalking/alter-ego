import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import {
  DASHBOARD_CHAT_BG_HEADER,
  DASHBOARD_CHAT_BORDER_SUBTLE,
  DASHBOARD_CHAT_BORDER_LIGHT,
  DASHBOARD_CHAT_MONO_FONT,
  DASHBOARD_CHAT_TEXT_DIM,
  DASHBOARD_CHAT_TEXT_MUTED,
} from "@/modules/editorial-operations";

export interface ChatHeaderProps {
  onNewChat?: () => void;
  /** Toggle the conversation drawer (mobile only). */
  onToggleConversations?: () => void;
  conversationsOpen?: boolean;
  conversationsId?: string;
  /**
   * In the public shell there is no dashboard menu button to clear, so the bar
   * drops the left gutter the dashboard needs for it, and it is a plain `div`:
   * the site header above it is the page's only banner landmark.
   */
  publicShell?: boolean;
}

/**
 * `pl-14` clears the layout-level mobile hamburger (z-50); layout uses Tailwind
 * so the header reflows while the neon surface styling stays inline. The
 * panel-left icon is distinct from the global nav hamburger: it toggles the
 * conversation list, not site navigation.
 */
export function ChatHeader({
  onNewChat,
  onToggleConversations,
  conversationsOpen,
  conversationsId,
  publicShell = false,
}: Readonly<ChatHeaderProps>): React.ReactElement {
  const t = useTranslations("chat");
  const Bar = publicShell ? "div" : "header";
  return (
    <Bar
      className={cn(
        "sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between gap-2 pr-4 md:pr-8",
        publicShell ? "pl-4 md:pl-8" : "pl-16 lg:pl-8",
      )}
      style={{
        borderBottom: `1px solid ${DASHBOARD_CHAT_BORDER_SUBTLE}`,
        background: DASHBOARD_CHAT_BG_HEADER,
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        {onToggleConversations && (
          <button
            type="button"
            onClick={onToggleConversations}
            aria-label={
              conversationsOpen
                ? t("closeConversations")
                : t("openConversations")
            }
            aria-expanded={conversationsOpen}
            aria-controls={conversationsId}
            className="flex h-11 w-11 items-center justify-center rounded-md md:hidden"
            style={{
              border: `1px solid ${DASHBOARD_CHAT_BORDER_LIGHT}`,
              background: "transparent",
              color: DASHBOARD_CHAT_TEXT_MUTED,
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <path d="M9 4v16" />
            </svg>
          </button>
        )}
        <h1 style={{ fontSize: "16px", fontWeight: 700 }}>{t("title")}</h1>
        <span
          style={{
            fontFamily: DASHBOARD_CHAT_MONO_FONT,
            fontSize: "11px",
            color: DASHBOARD_CHAT_TEXT_DIM,
          }}
        >
          / <span>{t("subtitle")}</span>
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {onNewChat && (
          <button
            type="button"
            onClick={onNewChat}
            className="min-h-11 whitespace-nowrap"
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
            {t("input.newChat")}
          </button>
        )}
      </div>
    </Bar>
  );
}
