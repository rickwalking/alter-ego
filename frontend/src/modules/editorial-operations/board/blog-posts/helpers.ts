import { formatLocaleDate } from "@/lib/locale-format";
import type { DashboardBlogPost } from "./types";

/** Card date in the active locale (AE-0416/AE-0417: pt "17/10/2026", en "Oct 17, 2026"). */
export function formatBlogPostDate(date: string, locale: string): string {
  return formatLocaleDate(date, locale);
}

/**
 * The one post shown in the large "featured" slot: the newest post that is
 * actually live (AE-0411). Every other post renders as a regular card, so no
 * post is ever dropped from the list (B07).
 */
export function pickFeaturedBlogPost(
  posts: DashboardBlogPost[],
): DashboardBlogPost | undefined {
  return posts.find((post) => post.isPublic);
}
