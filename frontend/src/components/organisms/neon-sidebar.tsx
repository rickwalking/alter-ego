"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
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
import { SIDEBAR_WIDTH_PX } from "@/components/organisms/constants";

export interface NeonSidebarProps {
  sections: SidebarSection[];
  showUserFooter?: boolean;
}

export function NeonSidebar({
  sections,
  showUserFooter = false,
}: NeonSidebarProps): React.ReactElement {
  const pathname = usePathname();
  const t = useTranslations("common.sidebar");
  const { user, logout, isLoading } = useAuth();

  return (
    <aside
      className="fixed top-0 left-0 h-full flex flex-col"
      style={{
        width: `${SIDEBAR_WIDTH_PX}px`,
        background: BG_SIDEBAR,
        borderRight: `1px solid ${NEON_BORDER_SUBTLE}`,
        zIndex: 30,
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
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    padding: "10px 12px",
                    borderRadius: "6px",
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
          <img
            src="/about-pedro.png"
            alt=""
            style={{
              width: "28px",
              height: "28px",
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
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "28px",
              height: "28px",
              borderRadius: "6px",
              border: `1px solid ${NEON_BORDER_LIGHT}`,
              background: "transparent",
              color: TEXT_MUTED,
              cursor: "pointer",
              flexShrink: 0,
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
