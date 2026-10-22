"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { NeonIcon } from "@/components/atoms/neon-icon";
import { NeonBadge } from "@/components/atoms/neon-badge";
import {
  NEON_CYAN,
  NEON_CYAN_DIM,
  NEON_MAGENTA,
  NEON_MAGENTA_DIM,
  TEXT,
  NEON_SIDEBAR_LOGO_SHADOW,
  NEON_BORDER_SUBTLE,
  TEXT_DIM,
  TEXT_MUTED,
} from "@/constants/neon";
import type { SidebarSection } from "@/schemas/neon-sidebar";

/** Logo mark and product name. */
export function SidebarBrand(): React.ReactElement {
  return (
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
  );
}

/** Sections with the items the viewer may open; admin-only items need an admin. */
export function visibleSidebarSections(
  sections: SidebarSection[],
  isAdmin: boolean,
): SidebarSection[] {
  return sections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => !item.access || isAdmin),
    }))
    .filter((section) => section.items.length > 0);
}

/**
 * The section groups and their links, highlighting the current page.
 *
 * Nav links get a 44px+ touch target on coarse pointers and stay compact on
 * fine pointers to keep desktop density.
 */
export function SidebarNav({
  sections,
}: Readonly<{
  sections: SidebarSection[];
}>): React.ReactElement {
  const pathname = usePathname();
  const t = useTranslations("common.sidebar");
  return (
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
  );
}
