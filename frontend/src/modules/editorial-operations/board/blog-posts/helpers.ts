import type { DashboardBlogPost } from "./types";

/** BCP 47 tag per dashboard locale, so dates read "17 de out. de 2026" in PT. */
const DATE_LOCALES: Record<string, string> = { en: "en-US", pt: "pt-BR" };

/** Short post date in the dashboard language (AE-0416; was always en-US). */
export function formatBlogPostDate(date: string, locale: string): string {
  return new Date(date).toLocaleDateString(DATE_LOCALES[locale] ?? locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
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
