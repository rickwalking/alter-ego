import type { BlogPost } from "@/modules/publishing";
import { toBlogPostOrigin, toBlogPostStatus } from "@/modules/publishing";
import type { DashboardBlogPost } from "@/modules/editorial-operations/board/blog-posts/types";

const NO_CATEGORY = "";
const DEFAULT_LOCK_VERSION = 1;

export function mapBlogPostToDashboard(post: BlogPost): DashboardBlogPost {
  return {
    id: post.id,
    title: post.title,
    excerpt: post.excerpt ?? "",
    date: post.published_at ?? post.updated_at ?? post.created_at,
    views: post.view_count,
    comments: post.comment_count,
    origin: toBlogPostOrigin(post.origin),
    lockVersion: post.lock_version ?? DEFAULT_LOCK_VERSION,
    status: toBlogPostStatus(post.status),
    // Workflow status is NOT a content category (AE-0295 root cause) — no
    // backend field populates a category today, so it stays empty.
    category: NO_CATEGORY,
    featured: post.status === "published",
  };
}
