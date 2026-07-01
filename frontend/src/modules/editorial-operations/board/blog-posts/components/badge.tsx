import {
  BLOG_POST_BADGE_CLASS,
  BLOG_POST_BADGE_COLORS,
  BLOG_POST_BADGE_FALLBACK,
} from "../constants";
import type { BlogPostBadgeProps } from "./types";

export function BlogPostBadge({ children, color }: BlogPostBadgeProps) {
  const { bg, text } =
    BLOG_POST_BADGE_COLORS[color] ?? BLOG_POST_BADGE_FALLBACK;
  return (
    <span
      className={`${BLOG_POST_BADGE_CLASS} ${BLOG_POST_BADGE_CLASS}-${color}`}
      style={{ backgroundColor: bg, color: text }}
    >
      {children}
    </span>
  );
}
