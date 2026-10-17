import type { BlogPost } from "@/modules/publishing";
import { toBlogPostOrigin, toBlogPostStatus } from "@/modules/publishing";
import type { DashboardBlogPost } from "@/modules/editorial-operations/board/blog-posts/types";

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
    isPublic: post.is_public ?? false,
  };
}
