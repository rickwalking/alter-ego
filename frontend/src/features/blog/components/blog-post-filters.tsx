"use client";

import { useTranslations } from "next-intl";
import { Input } from "@/components/ui";

interface BlogPostFiltersProps {
  search: string;
  status: string;
  onSearchChange: (value: string) => void;
  onStatusChange: (value: string) => void;
}

const STATUS_OPTIONS = ["", "draft", "under_review", "approved", "published", "archived"];

export function BlogPostFilters({
  search,
  status,
  onSearchChange,
  onStatusChange,
}: BlogPostFiltersProps) {
  const t = useTranslations("dashboard.blogPosts");

  return (
    <div className="flex flex-col sm:flex-row gap-3 mb-6">
      <Input
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder={t("searchPlaceholder")}
        aria-label={t("searchPlaceholder")}
        className="sm:max-w-xs"
      />
      <select
        value={status}
        onChange={(e) => onStatusChange(e.target.value)}
        className="h-10 rounded-md border border-input bg-background px-3 text-sm sm:max-w-[200px]"
        aria-label={t("filterStatus")}
      >
        <option value="">{t("allStatuses")}</option>
        {STATUS_OPTIONS.filter(Boolean).map((s) => (
          <option key={s} value={s}>
            {t(`status.${s}`)}
          </option>
        ))}
      </select>
    </div>
  );
}
