import type { BlogPost } from "@/modules/publishing";
import type { DashboardBlogPost } from "@/modules/editorial-operations/board/blog-posts/types";

export function mapBlogPostToDashboard(post: BlogPost): DashboardBlogPost {
  return {
    id: post.id,
    title: post.title,
    excerpt: post.excerpt ?? "",
    date: post.published_at ?? post.updated_at ?? post.created_at,
    views: post.view_count,
    comments: post.comment_count,
    category: post.status,
    featured: post.status === "published",
  };
}
