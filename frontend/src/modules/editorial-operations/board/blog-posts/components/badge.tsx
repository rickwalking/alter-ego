import { BLOG_POST_BADGE_CLASS, BLOG_POST_BADGE_COLORS } from "../constants";

interface BlogPostBadgeProps {
  children: React.ReactNode;
  color: string;
}

export function BlogPostBadge({ children, color }: BlogPostBadgeProps) {
  const { bg, text } = BLOG_POST_BADGE_COLORS[color];
  return (
    <span
      className={`${BLOG_POST_BADGE_CLASS} ${BLOG_POST_BADGE_CLASS}-${color}`}
      style={{ backgroundColor: bg, color: text }}
    >
      {children}
    </span>
  );
}
