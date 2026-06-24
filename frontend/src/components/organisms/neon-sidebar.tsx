"use client";

import { useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { useFocusTrap } from "@/lib/use-focus-trap";
import { useScrollLock } from "@/lib/use-scroll-lock";
import { useMediaQuery } from "@/lib/use-media-query";
import { NeonIcon } from "@/components/atoms/neon-icon";
import { NeonBadge } from "@/components/atoms/neon-badge";
import {
  BG_SIDEBAR,
  NEON_CYAN,
  NEON_CYAN_DIM,
  NEON_MAGENTA,
  NEON_MAGENTA_DIM,
  TEXT,
  NEON_BORDER_LIGHT,
  NEON_SIDEBAR_LOGO_SHADOW,
  NEON_BORDER_STRONG,
  NEON_BORDER_SUBTLE,
  TEXT_DIM,
  TEXT_MUTED,
} from "@/constants/neon";
import type { SidebarSection } from "@/schemas/neon-sidebar";
import { useAuth } from "@/modules/identity";
import { SIDEBAR_AVATAR_SIZE } from "@/components/organisms/constants";

export interface NeonSidebarProps {
  sections: SidebarSection[];
  showUserFooter?: boolean;
  /** Drawer open state (mobile off-canvas). Omit for an always-static rail. */
  open?: boolean;
  /** DOM id so the layout hamburger can wire `aria-controls`. */
  id?: string;
}

export function NeonSidebar({
  sections,
  showUserFooter = false,
  open,
  id,
}: NeonSidebarProps): React.ReactElement {
  const pathname = usePathname();
  const t = useTranslations("common.sidebar");
  const { user, logout, isLoading } = useAuth();
  const asideRef = useRef<HTMLElement>(null);
  const isOpen = open === true;
  // Trap/lock ONLY while the drawer is actually off-canvas (below lg). At lg+
  // the rail is persistent, so an open flag must not lock scroll or trap focus.
  const isDrawer = useMediaQuery("(max-width: 1023px)");
  const drawerActive = isOpen && isDrawer;

  // Drawer a11y: trap focus and lock body scroll only while open on mobile.
  useFocusTrap(asideRef, drawerActive);
  useScrollLock(drawerActive);

  return (
    <aside
      ref={asideRef}
      id={id}
      aria-label={t("ariaLabel")}
      className={cn(
        // Off-canvas drawer below lg, persistent rail at lg+.
        // 240px == SIDEBAR_WIDTH_PX (kept in sync by a unit test). A literal,
        // not a CSS var, because a Tailwind v4 @theme var was tree-shaken out.
        "fixed inset-y-0 left-0 z-40 flex w-[240px] flex-col",
        "transition-transform duration-200 ease-out lg:translate-x-0",
        isOpen ? "translate-x-0" : "-translate-x-full",
      )}
      style={{
        background: BG_SIDEBAR,
        borderRight: `1px solid ${NEON_BORDER_SUBTLE}`,
      }}
    >
      <div
        style={{
          height: "56px",
          borderBottom: `1px solid ${NEON_BORDER_SUBTLE}`,
          display: "flex",
          alignItems: "center",
          padding: "0 20px",
        }}
      >
        <div
          style={{
            width: "32px",
            height: "32px",
            border: `2px solid ${NEON_CYAN}`,
            borderRadius: "4px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize: "14px",
            fontWeight: 700,
            color: NEON_CYAN,
            boxShadow: NEON_SIDEBAR_LOGO_SHADOW,
          }}
        >
          P
        </div>
        <div style={{ marginLeft: "12px" }}>
          <div style={{ fontSize: "16px", fontWeight: 700, color: TEXT }}>
            Alter Ego
          </div>
          <div
            style={{
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
              fontSize: "9px",
              color: TEXT_DIM,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            v2.0 · Neon Shell
          </div>
        </div>
      </div>

      <nav
        style={{
          flex: 1,
          padding: "12px",
          display: "flex",
          flexDirection: "column",
          gap: "4px",
        }}
      >
        {sections.map((group) => (
          <div key={group.sectionKey}>
            <div
              style={{
                fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                fontSize: "9px",
                textTransform: "uppercase",
                letterSpacing: "0.15em",
                color: TEXT_DIM,
                padding: "12px 12px 8px",
              }}
            >
              {t(group.sectionKey)}
            </div>
            {group.items.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  // Touch target: ≥44px on coarse pointers (touch), compact on
                  // fine pointers (mouse) to preserve desktop density.
                  className="flex items-center gap-3 rounded-md px-3 py-2.5 [@media(pointer:coarse)]:min-h-11"
                  style={{
                    color: isActive ? NEON_CYAN : TEXT_MUTED,
                    textDecoration: "none",
                    fontSize: "13px",
                    fontWeight: isActive ? 600 : 500,
                    transition: "all 0.15s",
                    background: isActive ? NEON_CYAN_DIM : "transparent",
                  }}
                >
                  <NeonIcon path={item.icon} />
                  <span style={{ flex: 1 }}>{t(item.labelKey)}</span>
                  {item.badge && (
                    <NeonBadge
                      variant="magenta"
                      size="sm"
                      style={{
                        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                        background: NEON_MAGENTA_DIM,
                        color: NEON_MAGENTA,
                      }}
                    >
                      {item.badge}
                    </NeonBadge>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {showUserFooter && !isLoading && user && (
        <div
          style={{
            padding: "12px",
            borderTop: `1px solid ${NEON_BORDER_SUBTLE}`,
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}
        >
          <Image
            src="/about-pedro.jpg"
            alt="Pedro"
            width={SIDEBAR_AVATAR_SIZE}
            height={SIDEBAR_AVATAR_SIZE}
            style={{
              borderRadius: "50%",
              border: `1px solid ${NEON_BORDER_STRONG}`,
              objectFit: "cover",
            }}
          />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: "12px",
                fontWeight: 600,
                color: TEXT,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {user.full_name}
            </div>
            <div
              style={{
                fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                fontSize: "9px",
                color: TEXT_DIM,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {user.email}
            </div>
          </div>
          <button
            type="button"
            onClick={() => logout()}
            aria-label="Logout"
            title="Logout"
            // ≥44px tap target on touch devices; compact for mouse.
            className="flex shrink-0 items-center justify-center rounded-md h-7 w-7 [@media(pointer:coarse)]:h-11 [@media(pointer:coarse)]:w-11"
            style={{
              border: `1px solid ${NEON_BORDER_LIGHT}`,
              background: "transparent",
              color: TEXT_MUTED,
              cursor: "pointer",
            }}
          >
            <NeonIcon
              path="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5M21 12H9"
              size={14}
            />
          </button>
        </div>
      )}
    </aside>
  );
}
