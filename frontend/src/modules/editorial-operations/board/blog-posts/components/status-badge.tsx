"use client";

import { useTranslations } from "next-intl";
import {
  BLOG_POST_BADGE_CLASS,
  BLOG_POST_BADGE_FALLBACK,
  BLOG_POST_NOT_LIVE_COLORS,
  BLOG_POST_STATUS_COLORS,
  BLOG_POSTS_I18N_NAMESPACE,
} from "../constants";
import type { BlogPostBadgeLook } from "../types";
import type { BlogPostStatusBadgeProps } from "./types";

const UNKNOWN_STATUS_KEY = "unknown";
const NOT_LIVE_STATUS_KEY = "notLive";
const PUBLISHED_STATUS = "published";

function resolveBadge({
  status,
  isPublic,
}: BlogPostStatusBadgeProps): BlogPostBadgeLook {
  if (!status) {
    return { key: UNKNOWN_STATUS_KEY, visual: BLOG_POST_BADGE_FALLBACK };
  }
  if (status === PUBLISHED_STATUS && isPublic === false) {
    return { key: NOT_LIVE_STATUS_KEY, visual: BLOG_POST_NOT_LIVE_COLORS };
  }
  return { key: status, visual: BLOG_POST_STATUS_COLORS[status] };
}

/**
 * Workflow-status badge (AE-0295). The `status` prop is typed as
 * `BlogPostStatus | null` — handing it an arbitrary string (e.g. a carousel
 * workflow status) is a compile error; `null` marks a drifted/unknown backend
 * value and renders the neutral fallback. A `published` post that is not
 * publicly readable yet renders "not public yet" (AE-0411).
 */
export function BlogPostStatusBadge(props: BlogPostStatusBadgeProps) {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  const { key, visual } = resolveBadge(props);
  return (
    <span
      className={`${BLOG_POST_BADGE_CLASS} ${BLOG_POST_BADGE_CLASS}-status-${key}`}
      style={{ backgroundColor: visual.bg, color: visual.text }}
    >
      {t(`status.${key}`)}
    </span>
  );
}
