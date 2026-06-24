"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { ROUTE_PATHS } from "@/constants/api";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { useAuth } from "@/modules/identity";

export function MobileNav() {
  const t = useTranslations("common.nav");
  const { user, isEditor, isAdmin } = useAuth();
  const isAuthenticated = user !== null;
  const [open, setOpen] = useState(false);

  return (
    <div className="md:hidden">
      <button
        type="button"
        aria-label="Open menu"
        className="text-sm px-2 py-1 border rounded"
        onClick={() => setOpen((v) => !v)}
      >
        ☰
      </button>
      {open && (
        <nav className="absolute left-0 right-0 top-14 z-40 border-b bg-background p-4 flex flex-col gap-3 text-sm shadow-md">
          {isAuthenticated && (
            <Link href={DASHBOARD_ROUTES.CHAT} onClick={() => setOpen(false)}>
              {t("chat")}
            </Link>
          )}
          {isEditor && (
            <Link
              href={DASHBOARD_ROUTES.KNOWLEDGE}
              onClick={() => setOpen(false)}
            >
              {t("knowledgeBase")}
            </Link>
          )}
          <Link href={ROUTE_PATHS.BLOG} onClick={() => setOpen(false)}>
            {t("blog")}
          </Link>
          {isEditor && (
            <Link href={DASHBOARD_ROUTES.CREATE} onClick={() => setOpen(false)}>
              {t("create")}
            </Link>
          )}
          {isEditor && (
            <Link
              href={DASHBOARD_ROUTES.PERSONAS}
              onClick={() => setOpen(false)}
            >
              {t("personas")}
            </Link>
          )}
          {isEditor && (
            <Link
              href={DASHBOARD_ROUTES.RUBRICS}
              onClick={() => setOpen(false)}
            >
              {t("rubrics")}
            </Link>
          )}
          {isEditor && (
            <Link
              href={DASHBOARD_ROUTES.PALETTES}
              onClick={() => setOpen(false)}
            >
              {t("palettes")}
            </Link>
          )}
          {isEditor && (
            <Link
              href={DASHBOARD_ROUTES.BLOG_POSTS}
              onClick={() => setOpen(false)}
            >
              {t("blogPosts")}
            </Link>
          )}
          {isEditor && (
            <Link
              href={DASHBOARD_ROUTES.WORKFLOW}
              onClick={() => setOpen(false)}
            >
              {t("workflow")}
            </Link>
          )}
          {isEditor && (
            <Link
              href={DASHBOARD_ROUTES.CALENDAR}
              onClick={() => setOpen(false)}
            >
              {t("calendar")}
            </Link>
          )}
          {isEditor && (
            <Link
              href={DASHBOARD_ROUTES.ANALYTICS}
              onClick={() => setOpen(false)}
            >
              {t("analytics")}
            </Link>
          )}
          {isAdmin && (
            <Link href={ROUTE_PATHS.ADMIN_USERS} onClick={() => setOpen(false)}>
              {t("admin")}
            </Link>
          )}
        </nav>
      )}
    </div>
  );
}
