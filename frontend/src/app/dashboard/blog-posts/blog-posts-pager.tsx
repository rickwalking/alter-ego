"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { BLOG_POSTS_I18N_NAMESPACE } from "@/modules/editorial-operations";
import { TEXT_DIM } from "@/constants/neon";
import type { BlogPostsPagerProps } from "@/app/dashboard/blog-posts/types";

/** Previous / next pages of the dashboard blog list. */
export function BlogPostsPager({
  page,
  pageCount,
  onPageChange,
}: Readonly<BlogPostsPagerProps>): React.ReactElement | null {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  if (pageCount <= 1) {
    return null;
  }
  return (
    <nav
      aria-label={t("pager.label")}
      className="flex items-center justify-center gap-3 pt-2"
    >
      <NeonButton
        size="sm"
        variant="secondary"
        disabled={page <= 0}
        onClick={() => onPageChange(page - 1)}
      >
        {t("pager.previous")}
      </NeonButton>
      <span
        aria-live="polite"
        className="font-mono text-[11px]"
        style={{ color: TEXT_DIM }}
      >
        {t("pager.status", { page: page + 1, count: pageCount })}
      </span>
      <NeonButton
        size="sm"
        variant="secondary"
        disabled={page >= pageCount - 1}
        onClick={() => onPageChange(page + 1)}
      >
        {t("pager.next")}
      </NeonButton>
    </nav>
  );
}
