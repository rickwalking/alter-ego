import type { BlogPost } from "@/features/blog/types";
import type { DashboardBlogPost } from "@/features/dashboard/blog-posts/types";

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
