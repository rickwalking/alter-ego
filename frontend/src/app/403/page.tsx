"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

export default function ForbiddenPage() {
  const t = useTranslations("auth");

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-900">403</h1>
        <p className="mt-4 text-xl text-gray-600">{t("forbiddenTitle")}</p>
        <p className="mt-2 text-sm text-gray-500">{t("forbiddenDescription")}</p>
        <Link
          href="/"
          className="mt-6 inline-block rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
        >
          {t("goHome")}
        </Link>
      </div>
    </div>
  );
}
