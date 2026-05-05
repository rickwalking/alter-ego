"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useAuth } from "@/hooks/use-auth";

export function AdminSidebar() {
  const t = useTranslations("admin");
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 bg-white shadow-sm">
      <div className="p-6">
        <h2 className="text-lg font-semibold text-gray-900">
          {t("panelTitle")}
        </h2>
        <p className="mt-1 text-xs text-gray-500">{user?.email}</p>
      </div>
      <nav className="px-4 pb-4">
        <Link
          href="/admin/users"
          className="block rounded-md px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
        >
          {t("usersLink")}
        </Link>
      </nav>
      <div className="absolute bottom-0 w-64 p-4">
        <button
          onClick={logout}
          className="w-full rounded-md px-4 py-2 text-sm font-medium text-destructive hover:bg-destructive/10"
        >
          {t("logout")}
        </button>
      </div>
    </aside>
  );
}
