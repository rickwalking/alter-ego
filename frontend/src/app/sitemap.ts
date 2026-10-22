import type { MetadataRoute } from "next";
import { SITE_URL } from "@/constants/api";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { SITEMAP } from "@/constants/sitemap";
import { fetchPublicBlogPosts, fetchPublicCarousels } from "@/lib/server-fetch";

export const revalidate = 3600;

type SitemapEntry = MetadataRoute.Sitemap[number];

interface FeedPage<T> {
  items: T[];
  total: number;
}

const FEED_CACHE = { revalidate: SITEMAP.REVALIDATE_SECONDS };

function siteUrl(path: string): string {
  return path === PUBLIC_ROUTE_PATHS.HOME ? SITE_URL : `${SITE_URL}${path}`;
}

function pageEntry(path: string, priority: number): SitemapEntry {
  return {
    url: siteUrl(path),
    changeFrequency: SITEMAP.PAGE_CHANGE_FREQUENCY,
    priority,
  };
}

function pageEntries(): SitemapEntry[] {
  return [
    pageEntry(PUBLIC_ROUTE_PATHS.HOME, SITEMAP.HOME_PRIORITY),
    pageEntry(PUBLIC_ROUTE_PATHS.BLOG, SITEMAP.SECTION_PRIORITY),
    pageEntry(PUBLIC_ROUTE_PATHS.CAROUSELS, SITEMAP.SECTION_PRIORITY),
    pageEntry(PUBLIC_ROUTE_PATHS.CHAT, SITEMAP.SECTION_PRIORITY),
  ];
}

function contentEntry(
  path: string,
  modified: string | null | undefined,
): SitemapEntry {
  return {
    url: siteUrl(path),
    ...(modified ? { lastModified: new Date(modified) } : {}),
    changeFrequency: SITEMAP.CONTENT_CHANGE_FREQUENCY,
    priority: SITEMAP.CONTENT_PRIORITY,
  };
}

/**
 * Every item of a paged feed: pages until the reported total is reached, a
 * page is empty or unavailable, or the safety cap of pages is hit.
 */
async function collectFeed<T>(
  fetchPage: (offset: number) => Promise<FeedPage<T> | null>,
  pageSize: number,
): Promise<T[]> {
  const items: T[] = [];
  for (let page = 0; page < SITEMAP.MAX_PAGES_PER_FEED; page += 1) {
    const result = await fetchPage(page * pageSize);
    if (!result || result.items.length === 0) break;
    items.push(...result.items);
    if (items.length >= result.total) break;
  }
  return items;
}

/**
 * Production URLs of the public pages, every published blog post and every
 * public completed carousel. Drafts never reach these feeds, and an
 * unavailable feed only drops its own entries. Cached for an hour so crawls
 * do not hit the rate-limited public feeds on every request.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [posts, carousels] = await Promise.all([
    collectFeed(
      (offset) =>
        fetchPublicBlogPosts(SITEMAP.BLOG_POST_PAGE_SIZE, offset, FEED_CACHE),
      SITEMAP.BLOG_POST_PAGE_SIZE,
    ),
    collectFeed(
      (offset) =>
        fetchPublicCarousels(SITEMAP.CAROUSEL_PAGE_SIZE, offset, FEED_CACHE),
      SITEMAP.CAROUSEL_PAGE_SIZE,
    ),
  ]);
  return [
    ...pageEntries(),
    ...posts.map((post) =>
      contentEntry(PUBLIC_ROUTE_PATHS.BLOG_POST(post.id), post.published_at),
    ),
    ...carousels.map((carousel) =>
      contentEntry(
        PUBLIC_ROUTE_PATHS.CAROUSEL_VIEWER(carousel.id),
        carousel.updated_at,
      ),
    ),
  ];
}
