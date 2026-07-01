"use client";

import { useTranslations } from "next-intl";
import {
  BLOG_POST_BADGE_CLASS,
  BLOG_POST_BADGE_FALLBACK,
  BLOG_POST_STATUS_COLORS,
  BLOG_POSTS_I18N_NAMESPACE,
} from "../constants";
import type { BlogPostStatusBadgeProps } from "./types";

const UNKNOWN_STATUS_KEY = "unknown";

/**
 * Workflow-status badge (AE-0295). The `status` prop is typed as
 * `BlogPostStatus | null` — handing it an arbitrary string (e.g. a carousel
 * workflow status) is a compile error; `null` marks a drifted/unknown backend
 * value and renders the neutral fallback.
 */
export function BlogPostStatusBadge({ status }: BlogPostStatusBadgeProps) {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  const { bg, text } = status
    ? BLOG_POST_STATUS_COLORS[status]
    : BLOG_POST_BADGE_FALLBACK;
  const statusKey = status ?? UNKNOWN_STATUS_KEY;
  return (
    <span
      className={`${BLOG_POST_BADGE_CLASS} ${BLOG_POST_BADGE_CLASS}-status-${statusKey}`}
      style={{ backgroundColor: bg, color: text }}
    >
      {t(`status.${statusKey}`)}
    </span>
  );
}
