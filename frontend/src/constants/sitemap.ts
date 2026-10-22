/** Sitemap feed sizes: the backend maximum page size of each public feed. */
export const SITEMAP = {
  BLOG_POST_LIMIT: 50,
  CAROUSEL_LIMIT: 100,
  PAGE_CHANGE_FREQUENCY: "weekly",
  CONTENT_CHANGE_FREQUENCY: "monthly",
  HOME_PRIORITY: 1,
  SECTION_PRIORITY: 0.8,
  CONTENT_PRIORITY: 0.6,
} as const;
