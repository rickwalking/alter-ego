/**
 * Single-post blog read used by the editor.
 *
 * The editor loads the post through the detail endpoint (the list endpoint
 * returns summaries without `content`, and only the first page). Writes live
 * in `blog-editor-requests.ts`.
 */

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { API_ENDPOINTS, HTTP_STATUS } from "@/constants/api";
import type { BlogPost } from "./types";

const ERR_LOAD_FAILED = "Failed to load blog post";

export const blogPostKeys = {
  detail: (id: string) => ["blog-post", id] as const,
};

/** GET /api/blog-posts/{id} — `null` when the post does not exist. */
export async function fetchBlogPostDetail(
  id: string,
): Promise<BlogPost | null> {
  const response = await authenticatedFetch(API_ENDPOINTS.BLOG_POST_BY_ID(id));
  if (response.status === HTTP_STATUS.NOT_FOUND) {
    return null;
  }
  if (!response.ok) {
    throw new Error(ERR_LOAD_FAILED);
  }
  return (await response.json()) as BlogPost;
}
