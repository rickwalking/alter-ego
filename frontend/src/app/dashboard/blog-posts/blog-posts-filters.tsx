"use client";

import { useTranslations } from "next-intl";
import {
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

/**
 * Status filter + real post counter (AE-0411). The old category filter was
 * removed: posts carry no category on the backend, so it always emptied the
 * list (B20).
 */
export function BlogPostsFilters({
  statusFilter,
  onStatusFilterChange,
  shownCount,
  totalCount,
}: Readonly<BlogPostsFiltersProps>): React.ReactElement {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  const allShownKey = shownCount === 1 ? "countOne" : "countOther";
  const counter =
    shownCount === totalCount
      ? t(allShownKey, { count: shownCount })
      : t("countOfTotal", { count: shownCount, total: totalCount });
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
      </div>
      <span
        aria-live="polite"
        style={{
          fontFamily: "'JetBrains Mono', ui-monospace, monospace",
          fontSize: "11px",
          color: TEXT_DIM,
        }}
      >
        {counter}
      </span>
    </div>
  );
}
