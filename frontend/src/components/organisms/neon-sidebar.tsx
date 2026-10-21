"use client";

import { useRef } from "react";

import { useLocale, useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { useFocusTrap } from "@/lib/use-focus-trap";
import { useScrollLock } from "@/lib/use-scroll-lock";
import { useMediaQuery } from "@/lib/use-media-query";

import { BG_SIDEBAR, NEON_BORDER_SUBTLE } from "@/constants/neon";
import type { SidebarSection } from "@/schemas/neon-sidebar";
import { useAuth } from "@/modules/identity";

import { LanguageSwitcher } from "@/components/language-switcher";
import {
  SidebarBrand,
  SidebarNav,
} from "@/components/organisms/neon-sidebar-parts";
import { SidebarUserFooter } from "@/components/organisms/neon-sidebar-user-footer";

export interface NeonSidebarProps {
  sections: SidebarSection[];
  showUserFooter?: boolean;
  /** Drawer open state (mobile off-canvas). Omit for an always-static rail. */
  open?: boolean;
  /** DOM id so the layout hamburger can wire `aria-controls`. */
  id?: string;
}

/**
 * Off-canvas drawer below lg, persistent rail at lg+. Focus trap and body
 * scroll lock apply only while the drawer is open off-canvas: at lg+ an open
 * flag must not lock scroll or trap focus. The 240px width equals
 * SIDEBAR_WIDTH_PX (kept in sync by a unit test) and is a literal, not a CSS
 * var, because a Tailwind v4 @theme var was tree-shaken out. The rail carries
 * the EN/PT language switcher.
 */
export function NeonSidebar({
  sections,
  showUserFooter = false,
  open,
  id,
}: Readonly<NeonSidebarProps>): React.ReactElement {
  const t = useTranslations("common.sidebar");
  const locale = useLocale();
  const { user, logout, isLoading } = useAuth();
  const asideRef = useRef<HTMLElement>(null);
  const isOpen = open === true;
  const isDrawer = useMediaQuery("(max-width: 1023px)");
  const drawerActive = isOpen && isDrawer;

  useFocusTrap(asideRef, drawerActive);
  useScrollLock(drawerActive);

  return (
    <aside
      ref={asideRef}
      id={id}
      aria-label={t("ariaLabel")}
      className={cn(
        "fixed inset-y-0 left-0 z-40 flex w-[240px] flex-col",
        "transition-transform duration-200 ease-out lg:translate-x-0",
        isOpen ? "translate-x-0" : "-translate-x-full",
      )}
      style={{
        background: BG_SIDEBAR,
        borderRight: `1px solid ${NEON_BORDER_SUBTLE}`,
      }}
    >
      <SidebarBrand />

      <SidebarNav sections={sections} />

      <div
        data-testid="sidebar-language-switcher"
        style={{
          padding: "8px 20px",
          borderTop: `1px solid ${NEON_BORDER_SUBTLE}`,
        }}
      >
        <LanguageSwitcher currentLocale={locale} variant="neon" />
      </div>

      {showUserFooter && !isLoading && user && (
        <SidebarUserFooter user={user} onLogout={() => logout()} />
      )}
    </aside>
  );
}
