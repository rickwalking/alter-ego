"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { ROUTE_PATHS } from "@/constants/api";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { useAuth } from "@/modules/identity";

type NavAccess = "everyone" | "signedIn" | "editor" | "admin";

interface MobileNavItem {
  href: string;
  labelKey: string;
  access: NavAccess;
}

/** Menu order and who sees each entry. */
const MOBILE_NAV_ITEMS: readonly MobileNavItem[] = [
  { href: DASHBOARD_ROUTES.CHAT, labelKey: "chat", access: "signedIn" },
  {
    href: DASHBOARD_ROUTES.KNOWLEDGE,
    labelKey: "knowledgeBase",
    access: "editor",
  },
  { href: ROUTE_PATHS.BLOG, labelKey: "blog", access: "everyone" },
  { href: DASHBOARD_ROUTES.CREATE, labelKey: "create", access: "editor" },
  { href: DASHBOARD_ROUTES.PERSONAS, labelKey: "personas", access: "editor" },
  { href: DASHBOARD_ROUTES.RUBRICS, labelKey: "rubrics", access: "editor" },
  { href: DASHBOARD_ROUTES.PALETTES, labelKey: "palettes", access: "editor" },
  {
    href: DASHBOARD_ROUTES.BLOG_POSTS,
    labelKey: "blogPosts",
    access: "editor",
  },
  { href: DASHBOARD_ROUTES.WORKFLOW, labelKey: "workflow", access: "editor" },
  { href: DASHBOARD_ROUTES.CALENDAR, labelKey: "calendar", access: "editor" },
  { href: DASHBOARD_ROUTES.ANALYTICS, labelKey: "analytics", access: "editor" },
  { href: ROUTE_PATHS.ADMIN_USERS, labelKey: "admin", access: "admin" },
];

export function MobileNav() {
  const t = useTranslations("common.nav");
  const { user, isEditor, isAdmin } = useAuth();
  const [open, setOpen] = useState(false);
  const allowed: Record<NavAccess, boolean> = {
    everyone: true,
    signedIn: user !== null,
    editor: isEditor,
    admin: isAdmin,
  };

  return (
    <div className="md:hidden">
      <button
        type="button"
        aria-label={t("openMenu")}
        className="text-sm px-2 py-1 border rounded"
        onClick={() => setOpen((v) => !v)}
      >
        ☰
      </button>
      {open && (
        <nav className="absolute left-0 right-0 top-14 z-40 border-b bg-background p-4 flex flex-col gap-3 text-sm shadow-md">
          {MOBILE_NAV_ITEMS.filter((item) => allowed[item.access]).map(
            (item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
              >
                {t(item.labelKey)}
              </Link>
            ),
          )}
        </nav>
      )}
    </div>
  );
}
