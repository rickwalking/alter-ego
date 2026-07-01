"use client";

import { useTranslations } from "next-intl";
import {
  BLOG_POST_CATEGORY_OPTIONS,
  BLOG_POST_STATUS_FILTER_VALUES,
  BLOG_POSTS_I18N_NAMESPACE,
} from "@/modules/editorial-operations";
import { NEON_BORDER_STRONG, NEON_INPUT_BG, TEXT_DIM } from "@/constants/neon";
import type { BlogPostsFiltersProps } from "@/app/dashboard/blog-posts/types";

const SELECT_STYLE = {
  padding: "6px 30px 6px 10px",
  fontSize: "12px",
  border: `1px solid ${NEON_BORDER_STRONG}`,
  background: NEON_INPUT_BG,
  color: "white",
  borderRadius: "4px",
  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  outline: "none",
} as const;

export function BlogPostsFilters({
  statusFilter,
  categoryFilter,
  onStatusFilterChange,
  onCategoryFilterChange,
}: BlogPostsFiltersProps): React.ReactElement {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  return (
    <div className="flex items-center justify-between flex-wrap gap-3">
      <div className="flex gap-2">
        <select
          style={SELECT_STYLE}
          value={statusFilter}
          aria-label={t("filterStatus")}
          onChange={(e) => onStatusFilterChange(e.target.value)}
        >
          <option value="">{t("allStatuses")}</option>
          {BLOG_POST_STATUS_FILTER_VALUES.map((status) => (
            <option key={status} value={status}>
              {t(`status.${status}`)}
            </option>
          ))}
        </select>
        <select
          style={SELECT_STYLE}
          value={categoryFilter}
          onChange={(e) => onCategoryFilterChange(e.target.value)}
        >
          {BLOG_POST_CATEGORY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
      <span
        style={{
          fontFamily: "'JetBrains Mono', ui-monospace, monospace",
          fontSize: "11px",
          color: TEXT_DIM,
        }}
      >
        24 posts
      </span>
    </div>
  );
}
