"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";

export function MobileNav() {
  const t = useTranslations("common.nav");
  const { isEditor, isAdmin } = useAuth();
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
          <Link href="/chat" onClick={() => setOpen(false)}>{t("chat")}</Link>
          {isEditor && <Link href="/knowledge" onClick={() => setOpen(false)}>{t("knowledgeBase")}</Link>}
          <Link href="/blog" onClick={() => setOpen(false)}>{t("blog")}</Link>
          {isEditor && <Link href="/create" onClick={() => setOpen(false)}>{t("create")}</Link>}
          {isEditor && <Link href="/personas" onClick={() => setOpen(false)}>{t("personas")}</Link>}
          {isEditor && <Link href="/rubrics" onClick={() => setOpen(false)}>{t("rubrics")}</Link>}
          {isEditor && <Link href="/blog-posts" onClick={() => setOpen(false)}>{t("blogPosts")}</Link>}
          {isEditor && <Link href="/workflow" onClick={() => setOpen(false)}>{t("workflow")}</Link>}
          {isEditor && <Link href="/calendar" onClick={() => setOpen(false)}>{t("calendar")}</Link>}
          {isEditor && <Link href="/analytics" onClick={() => setOpen(false)}>{t("analytics")}</Link>}
          {isAdmin && <Link href="/admin/users" onClick={() => setOpen(false)}>{t("admin")}</Link>}
        </nav>
      )}
    </div>
  );
}
